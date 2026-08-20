// The transcript sentence list and seek behavior for the player.
import { formatClock } from "./format.js";
import { speakerTag } from "./speakers.js";

const $ = (id) => document.getElementById(id);

let sentenceIndex = {};
let activeSentenceRow = null;
let speakerLabels = {};

export function setSpeakerLabels(labels) {
  speakerLabels = labels;
}

export function getSpeakerLabels() {
  return speakerLabels;
}

// Convert a sentence lookup by id into a seek on the player plus row highlight.
export function seekToSentence(sentenceId) {
  const sentence = sentenceIndex[sentenceId];
  if (!sentence) return;
  const player = $("player");
  player.currentTime = sentence.start;
  player.play().catch(() => {});
  _highlight(`[data-sid="${sentenceId}"]`);
}

// The full sentence list always renders; the meeting is a single-user artifact
// and a typical transcript is well under the size where preview would matter.
export function renderSentences(job) {
  const list = $("sentence-list");
  list.innerHTML = "";
  activeSentenceRow = null; // rows were rebuilt; any prior row reference is stale
  sentenceIndex = Object.fromEntries(job.sentences.map((s) => [s.id, s]));

  for (const sentence of job.sentences) {
    list.appendChild(_buildSentenceRow(sentence));
  }
}

function _highlight(selector) {
  if (activeSentenceRow) activeSentenceRow.classList.remove("is-active");
  const row = document.querySelector(`.sentence-row${selector}`);
  if (row) {
    row.classList.add("is-active");
    row.scrollIntoView({ block: "nearest", behavior: "smooth" });
    activeSentenceRow = row;
  }
}

function _buildSentenceRow(sentence) {
  const li = document.createElement("li");
  li.className = "sentence-row";
  li.dataset.sid = sentence.id;
  li.tabIndex = 0;
  li.addEventListener("click", () => _activate(li, sentence));
  li.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      _activate(li, sentence);
    }
  });

  const seek = document.createElement("span");
  seek.className = "sentence-seek";
  const time = document.createElement("span");
  time.className = "sentence-time";
  // The Latin time badge sits inside Arabic text, so it is wrapped in bdi to
  // keep direction from being mangled.
  const bdi = document.createElement("bdi");
  bdi.textContent = formatClock(sentence.start);
  time.appendChild(bdi);
  const playIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  playIcon.setAttribute("viewBox", "0 0 16 16");
  playIcon.classList.add("sentence-play");
  playIcon.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "#i-play");
  playIcon.appendChild(use);
  seek.append(time, playIcon);

  const speakerHost = document.createElement("span");
  speakerHost.className = "sentence-speaker";
  if (sentence.speaker && speakerLabels[sentence.speaker]) {
    li.dataset.speaker = sentence.speaker;
    speakerHost.appendChild(speakerTag(sentence.speaker, speakerLabels[sentence.speaker]));
  }

  const text = document.createElement("p");
  text.className = "sentence-text";
  text.textContent = sentence.text;

  li.append(seek, speakerHost, text);
  return li;
}

function _activate(li, sentence) {
  seekToSentence(sentence.id);
  if (activeSentenceRow) activeSentenceRow.classList.remove("is-active");
  li.classList.add("is-active");
  activeSentenceRow = li;
}
