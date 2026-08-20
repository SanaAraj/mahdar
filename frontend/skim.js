// Word-level seek bar: a row of ticks, one per sentence (real data), each
// click jumps the player to that sentence's start; a play/pause button and a
// current/total time readout flank the strip. The strip fills live as playback
// advances, so nothing is baked-in.

import { formatClock } from "./format.js";
import { STRINGS } from "./strings.js";

const $ = (id) => document.getElementById(id);

const state = {
  player: null,
  sentences: [],
  ticks: [],
  btn: null,
  timeLabel: null,
  onSeek: null,
};

export function initSkimBar(job, onSeek) {
  state.player = $("player");
  state.sentences = job.sentences || [];
  state.onSeek = onSeek;
  state.btn = $("skim-toggle");
  state.timeLabel = $("skim-time");

  const strip = $("skim-strip");
  strip.innerHTML = "";
  state.ticks = state.sentences.map((sentence, index) => {
    const tick = document.createElement("button");
    tick.className = "skim-tick";
    tick.type = "button";
    tick.dataset.sid = sentence.id;
    tick.title = `${index + 1} · ${sentence.text.slice(0, 40)}…`;
    tick.setAttribute("aria-label", tick.title);
    tick.addEventListener("click", () => onSeek(sentence.id));
    strip.appendChild(tick);
    return tick;
  });

  state.btn.addEventListener("click", togglePlayback);
  state.player.addEventListener("timeupdate", paint);
  state.player.addEventListener("play", paint);
  state.player.addEventListener("pause", paint);
  state.player.addEventListener("loadedmetadata", paint);
  paint();
}

function togglePlayback() {
  if (!state.player.src) return;
  if (state.player.paused) {
    state.player.play().catch(() => {});
  } else {
    state.player.pause();
  }
}

// Swap the toggle's icon between the play and pause symbols from index.html.
function setToggleIcon() {
  const use = state.btn.querySelector("use");
  use.setAttribute("href", state.player.paused ? "#i-play" : "#i-pause");
  state.btn.setAttribute("aria-label", state.player.paused ? STRINGS.play : STRINGS.pause);
}

function paint() {
  const current = state.player.currentTime;
  // Ticks before the player's position are filled; the active one is the
  // first unfilled whose start is still ahead (or the last when playing the end).
  for (let i = 0; i < state.ticks.length; i++) {
    state.ticks[i].classList.toggle("is-past", state.sentences[i].start <= current);
  }
  setToggleIcon();
  const total = state.player.duration;
  state.timeLabel.textContent = total
    ? `${formatClock(current)} / ${formatClock(total)}`
    : `${formatClock(current)} / --:--`;
}
