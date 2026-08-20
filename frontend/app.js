import { ApiClient } from "./api.js";
import {
  BYTES_PER_UPLOAD_MB,
  JOB_ID_RE,
  POLL_INTERVAL_MS,
  TIMER_TICK_MS,
} from "./config.js";
import { formatClock, formatDuration, metaLine } from "./format.js";
import { renderAnalysisBanner, renderMinutes } from "./minutes.js";
import { renderStats } from "./stats.js";
import { renderTasks } from "./tasks.js";
import { MeetingRecorder, blobToFile } from "./recorder.js";
import { initSkimBar } from "./skim.js";
import { renderSpeakersBar, speakerTag } from "./speakers.js";
import { renderStages } from "./stages.js";
import { STRINGS } from "./strings.js";
import {
  getSpeakerLabels,
  renderSentences,
  seekToSentence,
  setSpeakerLabels,
} from "./transcript.js";
import {
  clearRecording,
  hasRecording,
  initViews,
  keepRecording,
  setBanner,
  setError,
  show,
  takeRecording,
  takeUploadFile,
} from "./views.js";

const api = new ApiClient();
const recorder = new MeetingRecorder();

let pollTimer = null;
let timerInterval = null;
let elapsedSeconds = 0;

const $ = (id) => document.getElementById(id);

// ---------- recording ----------

async function beginRecording() {
  try {
    // The disc scales with the instantaneous mic level (0.9–1.35).
    recorder.onLevel = (level) => {
      $("rec-disc").style.setProperty("--pulse", (0.9 + level * 0.45).toFixed(3));
    };
    await recorder.start();
  } catch (err) {
    setError(err.message);
    return;
  }
  show("recording");
  $("view-recording").classList.remove("is-paused");
  $("btn-pause").querySelector("span").textContent = STRINGS.pause;
  $("btn-pause").querySelector("use").setAttribute("href", "#i-pause");
  startTimer();
}

async function finishRecording() {
  stopTimer();
  const blob = await recorder.stop();
  if (!blob || blob.size === 0) {
    setError(STRINGS.noAudioCaptured);
    return;
  }
  const file = blobToFile(blob, STRINGS.recordingBaseName);
  keepRecording(file, file.name);
  uploadCurrent();
}

function togglePause() {
  // The is-paused class drives both the disc color and the pause button state.
  const recordingView = $("view-recording");
  const pauseUse = $("btn-pause").querySelector("use");
  if (recorder.paused) {
    recorder.resume();
    recordingView.classList.remove("is-paused");
    $("btn-pause").querySelector("span").textContent = STRINGS.pause;
    pauseUse.setAttribute("href", "#i-pause");
  } else {
    recorder.pause();
    recordingView.classList.add("is-paused");
    $("btn-pause").querySelector("span").textContent = STRINGS.resume;
    pauseUse.setAttribute("href", "#i-play");
  }
}

function startTimer() {
  elapsedSeconds = 0;
  $("rec-timer").textContent = formatClock(0);
  stopTimer();
  timerInterval = setInterval(() => {
    if (!recorder.paused) {
      elapsedSeconds += 1;
      $("rec-timer").textContent = formatClock(elapsedSeconds);
    }
  }, TIMER_TICK_MS);
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
}

// ---------- uploading ----------

async function uploadCurrent() {
  if (!hasRecording()) {
    setError(STRINGS.noBlobToUpload);
    return;
  }
  const { file, filename } = takeRecording();
  // Courtesy pre-check before upload starts; the server cap is authoritative.
  if (file.size > BYTES_PER_UPLOAD_MB) {
    setError(STRINGS.fileTooLarge);
    return;
  }
  show("uploading");
  $("upload-fill").style.width = "0%";
  try {
    const result = await api.uploadAudio(file, filename, (pct) => {
      $("upload-fill").style.width = `${pct}%`;
    });
    setHashJob(result.id);
    startPolling(result.id);
  } catch (err) {
    // The server's Arabic reason when it sent one; the generic copy is for
    // a genuine network failure only.
    setError(err.detail || STRINGS.uploadFailed);
  }
}

// ---------- polling the job ----------

function startPolling(id) {
  show("processing");
  renderStages([]);
  stopPolling();
  poll(id);
}

function stopPolling() {
  if (pollTimer) clearTimeout(pollTimer);
  pollTimer = null;
}

async function poll(id) {
  try {
    const job = await api.getJob(id);
    renderStages(job.stages || []);
    if (job.status === "done") {
      stopPolling();
      renderDone(job);
      return;
    }
    if (job.status === "failed") {
      stopPolling();
      setError(job.error_ar || STRINGS.pollFailedGeneric);
      return;
    }
  } catch (err) {
    stopPolling();
    setError(err.detail || STRINGS.pollFailed);
    return;
  }
  pollTimer = setTimeout(() => poll(id), POLL_INTERVAL_MS);
}

// ---------- the finished view ----------

function renderDone(job) {
  show("done");
  $("header-actions").hidden = false;
  $("player").src = api.audioUrl(job.id);
  $("ready-badge").textContent = STRINGS.ready;
  $("done-meta").textContent = STRINGS.sentencesCount(job.sentences.length);
  const title = job.analysis ? job.analysis.title : "";
  $("meeting-title").textContent = title || STRINGS.meetingFallback;
  $("done-sub").textContent = metaLine(job, STRINGS);
  $("transcript-meta").textContent = STRINGS.sentencesCount(job.sentences.length);
  initExportLinks(job.id);
  renderAnalysisBanner(job, () => reanalyze(job.id));
  renderStats(job);
  renderSpeakers(job);
  renderMinutes(job, seekToSentence);
  renderTasks(job, seekToSentence);
  renderSentences(job);
  initSkimBar(job, seekToSentence);
}

// initExportLinks only sets the header action URLs; labels are sealed in HTML.
function initExportLinks(id) {
  const urls = api.exportUrls(id);
  $("export-docx").href = urls.docx;
  $("export-json").href = urls.json;
}

function renderSpeakers(job) {
  setSpeakerLabels(Object.fromEntries((job.speakers || []).map((s) => [s.id, s.label])));
  renderSpeakersBar($("speakers-bar"), job.speakers || [], api, job.id, $("player"), (updated) => {
    // The new label reflects on every sentence row at once, without a reload.
    setSpeakerLabels(Object.fromEntries(updated.map((s) => [s.id, s.label])));
    const labels = getSpeakerLabels();
    for (const row of document.querySelectorAll(".sentence-row")) {
      const tagHost = row.querySelector(".sentence-speaker");
      if (!tagHost) continue;
      tagHost.innerHTML = "";
      const sid = row.dataset.speaker;
      if (sid && labels[sid]) {
        tagHost.appendChild(speakerTag(sid, labels[sid]));
      }
    }
  });
}

async function reanalyze(id) {
  const banner = $("analysis-banner");
  setBanner(banner, STRINGS.analyzeRunning);
  try {
    await api.reanalyze(id);
    stopPolling();
    poll(id);
  } catch (err) {
    setBanner(banner, err.detail || STRINGS.pollFailedGeneric);
  }
}

// Leave the current meeting and return to the clean idle recording state.
// The meeting stays stored and reachable again through its #<id> link.
function resetSession() {
  stopPolling();
  stopTimer();
  recorder.reset();
  clearRecording();
  clearHashJob();
  const player = $("player");
  player.pause();
  player.removeAttribute("src");
  player.load();
  $("file-input").value = "";
  $("header-actions").hidden = true;
  $("view-recording").classList.remove("is-paused");
  show("idle");
}

// ---------- wiring ----------

// The meeting id lives in the hash (#<12 hex>) so a reload or shared link
// restores the job. Helpers keep the page URL payload (origin + path + hash)
// under the common ~2000-character URL cap; the origin plus this page adds
// well under 50 characters, so every valid id fits and no route redirects.
function meetingFromHash() {
  const id = location.hash.slice(1);
  return JOB_ID_RE.test(id) ? id : null;
}

function setHashJob(id) {
  history.replaceState(null, "", `#${id}`);
}

function clearHashJob() {
  history.replaceState(null, "", location.pathname);
}

// If the URL already points at a meeting, resume it; otherwise stay idle.
async function restoreFromHash() {
  const id = meetingFromHash();
  if (!id) return;
  try {
    const job = await api.getJob(id);
    if (job.status === "done") {
      renderDone(job);
    } else if (job.status === "failed") {
      setError(job.error_ar || STRINGS.pollFailedGeneric);
    } else {
      startPolling(id);
    }
  } catch (_err) {
    // Unknown or unreachable meeting: fresh clean state and a cleared hash.
    clearHashJob();
    show("idle");
  }
}

initViews();
restoreFromHash();

$("btn-record").addEventListener("click", beginRecording);
$("file-input").addEventListener("change", (e) => {
  const file = takeUploadFile(e.target.files[0]);
  if (file) uploadCurrent();
});
$("btn-stop").addEventListener("click", finishRecording);
$("btn-pause").addEventListener("click", togglePause);
$("btn-retry").addEventListener("click", () => {
  if (hasRecording()) {
    uploadCurrent();
  } else {
    clearRecording();
    show("idle");
  }
});

// Every "new meeting" control (done-view button, failed-view button, and the
// brand block, which is a div and so also needs its Enter and Space keys).
for (const el of document.querySelectorAll(".js-new-meeting")) {
  el.addEventListener("click", resetSession);
  if (el.tagName !== "BUTTON") {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        resetSession();
      }
    });
  }
}

window.addEventListener("beforeunload", (e) => {
  if (recorder.mediaRecorder && recorder.mediaRecorder.state === "recording") {
    e.preventDefault();
    e.returnValue = "";
  }
});

if (!recorder.supported()) {
  $("btn-record").disabled = true;
}
