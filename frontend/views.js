// The six single-page views and the failure surface. View switching, the
// banner gate, and the kept-recording store live here so app.js holds only
// the controller flow that drives them.

import { ALLOWED_EXTENSIONS, BYTES_PER_UPLOAD_MB } from "./config.js";
import { STRINGS } from "./strings.js";

const views = {};

export function initViews() {
  for (const name of ["idle", "recording", "uploading", "processing", "done", "failed"]) {
    views[name] = document.getElementById(`view-${name}`);
  }
}

export function show(name) {
  for (const [key, el] of Object.entries(views)) {
    el.classList.toggle("is-active", key === name);
    // A banner left visible in a hidden view resurfaces when that view shows
    // again. Collapse all banners on a view switch; the done-view failure
    // branch re-shows its banner from job data right after show("done").
    if (key !== name) {
      for (const banner of el.querySelectorAll(".analysis-banner")) {
        banner.hidden = true;
      }
    }
  }
}

// The one gate every banner-like box passes through: it renders only while it
// carries a non-empty message. An empty string wipes it and hides the panel,
// so the message and the visibility can never disagree.
export function setBanner(el, message) {
  el.innerHTML = "";
  if (!message) {
    el.hidden = true;
    return;
  }
  const p = document.createElement("p");
  p.className = "analysis-banner-text";
  p.textContent = message;
  el.appendChild(p);
  el.hidden = false;
}

export function setError(message) {
  document.getElementById("fail-message").textContent = message;
  show("failed");
}

// The current recording held in memory so a failed upload can be retried
// without the user re-recording. Lives here, not in the controller.
let currentBlob = null;
let currentFilename = null;

export function keepRecording(file, filename) {
  currentBlob = file;
  currentFilename = filename;
}

export function hasRecording() {
  return currentBlob !== null;
}

export function takeRecording() {
  return { file: currentBlob, filename: currentFilename };
}

export function clearRecording() {
  currentBlob = null;
  currentFilename = null;
}

// Validate a picked file against the allowed extensions and MIME type, keep it
// for the retry path, and return it (or null when rejected with an error shown).
export function takeUploadFile(file) {
  if (!file) return null;
  const ext = (file.name.match(/\.([A-Za-z0-9]+)$/) || [])[1] || "";
  const allowedType = file.type.startsWith("audio") || file.type.startsWith("video/mp4");
  if (!ALLOWED_EXTENSIONS.includes(ext.toLowerCase()) && !allowedType) {
    setError(STRINGS.invalidFile);
    return null;
  }
  // Courtesy pre-check before any upload starts; the server cap is authoritative.
  if (file.size > BYTES_PER_UPLOAD_MB) {
    setError(STRINGS.fileTooLarge);
    return null;
  }
  keepRecording(file, file.name);
  return file;
}
