// The follow-up tasks: one row per task, checkbox-shape at the inline start,
// due phrase at the inline end, then the owner line and the priority badge
// below the description. A row whose citation resolves seeks the player there.
import { makeSeekable, seekTargetOf } from "./minutes.js";
import { STRINGS } from "./strings.js";

const $ = (id) => document.getElementById(id);

function emptyNote(text) {
  const p = document.createElement("p");
  p.className = "note-empty";
  p.textContent = text;
  return p;
}

export function renderTasks(job, onSeek) {
  const section = $("tasks-section");
  section.innerHTML = "";
  if (!job.analysis) {
    section.appendChild(emptyNote(STRINGS.sectionsEmpty));
    return;
  }
  const tasks = job.analysis.tasks;
  if (!tasks.length) {
    section.appendChild(emptyNote(STRINGS.tasksEmpty));
    return;
  }
  const known = new Set((job.sentences || []).map((s) => s.id));
  const list = document.createElement("ul");
  list.className = "tasks-list";
  for (const task of tasks) {
    list.appendChild(buildTaskRow(task, known, onSeek));
  }
  section.appendChild(list);
}

function buildTaskRow(task, known, onSeek) {
  const li = document.createElement("li");
  li.className = "task-row";

  const box = document.createElement("span");
  box.className = "task-box";
  box.setAttribute("aria-hidden", "true");

  const body = document.createElement("div");
  body.className = "task-body";

  const head = document.createElement("div");
  head.className = "task-head";
  const desc = document.createElement("span");
  desc.className = "task-desc";
  desc.textContent = task.description;
  head.appendChild(desc);
  const due = dueLine(task.due);
  if (due) {
    head.appendChild(due);
  }

  body.appendChild(head);

  const owner = document.createElement("span");
  owner.className = "task-owner";
  owner.textContent = `${STRINGS.colOwner}: ${task.owner || STRINGS.taskOwnerFallback}`;
  body.appendChild(owner);

  if (task.priority) {
    const badge = document.createElement("span");
    badge.className = "priority-badge";
    badge.dataset.level = PRIORITY_LEVELS[task.priority] || "low";
    badge.textContent = task.priority;
    body.appendChild(badge);
  }

  const target = seekTargetOf(task, known);
  if (target) makeSeekable(li, target, onSeek);
  li.append(box, body);
  return li;
}

// One concise due string: Gregorian when the model normalized it, else the raw
// spoken phrase, with Hijri appended when both are available.
function dueLine(due) {
  const greg = due.gregorian || due.raw;
  if (!greg && !due.hijri) return null;
  const span = document.createElement("span");
  span.className = "task-due";
  const bdi = document.createElement("bdi");
  bdi.textContent = greg;
  span.appendChild(bdi);
  if (due.hijri && due.gregorian) {
    const sep = document.createElement("bdi");
    sep.textContent = ` · ${due.hijri}${STRINGS.hijriSuffix}`;
    span.appendChild(sep);
  }
  return span;
}

// Badge level keyed by the Arabic priority literal the model returns.
const PRIORITY_LEVELS = {
  [STRINGS.priorityHigh]: "high",
  [STRINGS.priorityMedium]: "medium",
};
