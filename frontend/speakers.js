import { CHIP_ERROR_MS, MAX_LABEL_LENGTH, PREVIEW_SECONDS, SPEAKER_PALETTE } from "./config.js";
import { STRINGS } from "./strings.js";

function speakerColor(id) {
  let hash = 0;
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return SPEAKER_PALETTE[hash % SPEAKER_PALETTE.length];
}

// Build the speakers bar above the transcript; text goes in via DOM only,
// never innerHTML, for any dynamic value.
export function renderSpeakersBar(container, speakers, api, jobId, player, onRenamed) {
  container.innerHTML = "";
  if (!speakers || speakers.length === 0) {
    container.hidden = true;
    return;
  }
  container.hidden = false;
  for (const speaker of speakers) {
    container.appendChild(buildChip(speaker, api, jobId, player, onRenamed));
  }
}

function buildChip(speaker, api, jobId, player, onRenamed) {
  const color = speakerColor(speaker.id);
  const chip = document.createElement("div");
  chip.className = "speaker-chip";
  chip.style.setProperty("--chip-bg", color.bg);
  chip.style.setProperty("--chip-ink", color.ink);
  chip.style.setProperty("--chip-ring", color.ring);

  const label = document.createElement("button");
  label.className = "speaker-chip-label";
  label.type = "button";
  label.textContent = speaker.label;
  label.setAttribute("aria-label", `${STRINGS.renameLabel}: ${speaker.label}`);

  const play = document.createElement("button");
  play.className = "speaker-chip-play";
  play.type = "button";
  play.title = STRINGS.playSample;
  play.setAttribute("aria-label", `${STRINGS.playSample}: ${speaker.label}`);
  play.appendChild(playIcon());

  chip.appendChild(label);
  chip.appendChild(play);

  label.addEventListener("click", () => openEditor(chip, speaker, api, jobId, onRenamed));
  play.addEventListener("click", () => playSample(player, speaker.first_start));
  return chip;
}

function openEditor(chip, speaker, api, jobId, onRenamed) {
  if (chip.dataset.editing === "1") return;
  chip.dataset.editing = "1";
  const color = speakerColor(speaker.id);
  const input = document.createElement("input");
  input.className = "speaker-chip-input";
  input.type = "text";
  input.maxLength = MAX_LABEL_LENGTH;
  input.value = speaker.label;
  input.setAttribute("aria-label", STRINGS.renameLabel);
  input.style.setProperty("--chip-ring", color.ring);

  const hint = document.createElement("span");
  hint.className = "speaker-chip-hint";
  hint.textContent = STRINGS.renameHint;

  const labelBtn = chip.querySelector(".speaker-chip-label");
  labelBtn.hidden = true;
  chip.insertBefore(hint, labelBtn);
  chip.insertBefore(input, hint);
  input.focus();
  input.select();

  let done = false;
  const finish = (save) => {
    if (done) return;
    done = true;
    if (save) {
      commit(input, chip, speaker, api, jobId, onRenamed);
    } else {
      restore(chip, speaker);
    }
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") finish(true);
    if (e.key === "Escape") finish(false);
  });
  input.addEventListener("blur", () => finish(true));
}

async function commit(input, chip, speaker, api, jobId, onRenamed) {
  const next = input.value.trim();
  if (!next || next === speaker.label) {
    restore(chip, speaker);
    return;
  }
  input.disabled = true;
  try {
    const updated = await api.renameSpeakers(jobId, { [speaker.id]: next });
    onRenamed(updated);
    restore(chip, { ...speaker, label: next });
  } catch (err) {
    input.disabled = false;
    restore(chip, speaker, err.detail || STRINGS.renameFailed);
  }
}

function restore(chip, speaker, errMessage) {
  chip.dataset.editing = "0";
  const input = chip.querySelector(".speaker-chip-input");
  if (input) input.remove();
  const hint = chip.querySelector(".speaker-chip-hint");
  if (hint) hint.remove();
  const labelBtn = chip.querySelector(".speaker-chip-label");
  labelBtn.hidden = false;
  labelBtn.textContent = speaker.label;
  labelBtn.setAttribute("aria-label", `${STRINGS.renameLabel}: ${speaker.label}`);
  showChipError(chip, errMessage);
}

let errorTimer = null;
function showChipError(chip, message) {
  const prev = chip.querySelector(".speaker-chip-error");
  if (prev) prev.remove();
  if (!message) return;
  const err = document.createElement("span");
  err.className = "speaker-chip-error";
  err.setAttribute("role", "alert");
  err.textContent = message;
  chip.appendChild(err);
  if (errorTimer) clearTimeout(errorTimer);
  errorTimer = setTimeout(() => err.remove(), CHIP_ERROR_MS);
}

// Play a short sample from a speaker's first segment to recognize their voice
// before naming them.
let sampleTimer = null;
function playSample(player, firstStart) {
  if (sampleTimer) clearTimeout(sampleTimer);
  player.currentTime = firstStart;
  player.play().catch(() => {});
  sampleTimer = setTimeout(() => player.pause(), PREVIEW_SECONDS * 1000);
}

function playIcon() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M4 2.5v11l9-5.5z");
  path.setAttribute("fill", "currentColor");
  svg.appendChild(path);
  return svg;
}

// Color and render the speaker tag inside a sentence row; no tag when null.
export function speakerTag(speakerId, label) {
  const color = speakerColor(speakerId);
  const tag = document.createElement("span");
  tag.className = "speaker-tag";
  tag.style.setProperty("--chip-bg", color.bg);
  tag.style.setProperty("--chip-ink", color.ink);
  tag.textContent = label;
  return tag;
}
