// Rendering of the processing-stage list during the "processing" view.

import { STRINGS } from "./strings.js";

const $ = (id) => document.getElementById(id);

const STAGE_ICONS = {
  pending:
    `<svg class="stage-icon" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="none" stroke="var(--color-line)" stroke-width="2"/></svg>`,
  running:
    `<svg class="stage-icon spinner" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="none" stroke="var(--color-accent)" stroke-width="2" stroke-dasharray="30 20"/></svg>`,
  done:
    `<svg class="stage-icon" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="none" stroke="var(--color-accent)" stroke-width="2"/><path d="M6 10l3 3 5-6" fill="none" stroke="var(--color-accent)" stroke-width="2"/></svg>`,
  error:
    `<svg class="stage-icon" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="none" stroke="var(--color-danger)" stroke-width="2"/><path d="M7 7l6 6M13 7l-6 6" stroke="var(--color-danger)" stroke-width="2"/></svg>`,
};

// Stage icons are static UI chrome, not server data, so innerHTML is safe here.
export function renderStages(stages) {
  const list = $("stage-list");
  list.innerHTML = "";
  for (const stage of stages) {
    const li = document.createElement("li");
    li.className = "stage-item";
    li.dataset.state = stage.state;

    const icon = document.createElement("span");
    icon.className = "stage-icon-slot";
    icon.innerHTML = STAGE_ICONS[stage.state] || STAGE_ICONS.pending;

    const label = document.createElement("span");
    label.textContent = stage.label_ar;

    li.appendChild(icon);
    li.appendChild(label);
    // A quiet note appears only while the diarize stage runs: on CPU it can
    // take about as long as the recording itself, so the user is not alarmed.
    if (stage.key === "diarize" && stage.state === "running") {
      const note = document.createElement("span");
      note.className = "stage-note";
      note.textContent = STRINGS.diarizeRunningNote;
      li.appendChild(note);
    }
    list.appendChild(li);
  }
}
