// The minutes section: attendee chips, topics as title-and-summary cards, then
// the decisions and directives groups, each with its designed empty line. A row
// whose citation resolves to a transcript sentence seeks the player there; a
// row without one stays plain, with no button affordances. Every text value
// goes in via textContent, never innerHTML.

import { STRINGS } from "./strings.js";
import { setBanner } from "./views.js";

const $ = (id) => document.getElementById(id);

function emptyNote(text) {
  const p = document.createElement("p");
  p.className = "note-empty";
  p.textContent = text;
  return p;
}

// First cited id that names a sentence of this meeting, or null.
export function seekTargetOf(item, known) {
  return (item.segment_ids || []).find((sid) => known.has(sid)) || null;
}

// Button semantics on a list row: pointer, focus, Enter and Space activation.
export function makeSeekable(li, target, onSeek) {
  li.classList.add("is-seekable");
  li.setAttribute("role", "button");
  li.tabIndex = 0;
  li.addEventListener("click", () => onSeek(target));
  li.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSeek(target);
    }
  });
}

export function renderMinutes(job, onSeek) {
  const section = $("minutes-section");
  section.innerHTML = "";
  const analysis = job.analysis;
  if (!analysis) {
    section.appendChild(emptyNote(STRINGS.sectionsEmpty));
    return;
  }
  const known = new Set((job.sentences || []).map((s) => s.id));
  if (analysis.attendees.length) {
    section.appendChild(buildAttendees(analysis.attendees));
  }
  section.appendChild(buildTopicsList(analysis.topics, known, onSeek));
  section.appendChild(
    buildPlainGroup(
      STRINGS.decisionsHeading,
      analysis.decisions,
      STRINGS.decisionsEmpty,
      known,
      onSeek,
    ),
  );
  section.appendChild(
    buildPlainGroup(
      STRINGS.directivesHeading,
      analysis.directives,
      STRINGS.directivesEmpty,
      known,
      onSeek,
    ),
  );
}

function buildAttendees(attendees) {
  const wrap = document.createElement("div");
  wrap.className = "minutes-attendees";
  const head = document.createElement("h4");
  head.className = "minutes-subhead";
  head.textContent = STRINGS.attendeesLabel;
  wrap.appendChild(head);
  const ul = document.createElement("ul");
  ul.className = "attendee-chips";
  for (const name of attendees) {
    const li = document.createElement("li");
    li.textContent = name;
    ul.appendChild(li);
  }
  wrap.appendChild(ul);
  return wrap;
}

function buildTopicsList(topics, known, onSeek) {
  const wrap = document.createElement("div");
  wrap.className = "minutes-group";
  if (!topics.length) {
    wrap.appendChild(emptyNote(STRINGS.topicsEmpty));
    return wrap;
  }
  const ul = document.createElement("ul");
  ul.className = "minutes-list";
  for (const topic of topics) {
    const li = document.createElement("li");
    const strong = document.createElement("strong");
    strong.textContent = topic.title;
    li.appendChild(strong);
    if (topic.summary) {
      const p = document.createElement("p");
      p.className = "minutes-summary";
      p.textContent = topic.summary;
      li.appendChild(p);
    }
    const target = seekTargetOf(topic, known);
    if (target) makeSeekable(li, target, onSeek);
    ul.appendChild(li);
  }
  wrap.appendChild(ul);
  return wrap;
}

// Decisions and directives stack under the topics cards; both use the same
// flat item style, each under its own heading.
function buildPlainGroup(heading, items, emptyText, known, onSeek) {
  const wrap = document.createElement("div");
  wrap.className = "minutes-group";
  const head = document.createElement("h4");
  head.className = "minutes-subhead";
  head.textContent = heading;
  wrap.appendChild(head);
  if (!items.length) {
    wrap.appendChild(emptyNote(emptyText));
    return wrap;
  }
  const ul = document.createElement("ul");
  ul.className = "minutes-plain";
  for (const item of items) {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.textContent = item.text;
    li.appendChild(span);
    const target = seekTargetOf(item, known);
    if (target) makeSeekable(li, target, onSeek);
    ul.appendChild(li);
  }
  wrap.appendChild(ul);
  return wrap;
}

/* ---- the analysis-failure banner with a retry button ---- */
export function renderAnalysisBanner(job, onRetry) {
  const banner = $("analysis-banner");
  banner.innerHTML = "";
  const failed = (job.stages || []).find((s) => s.key === "analyze" && s.state === "error");
  if (!failed) {
    banner.hidden = true;
    return;
  }
  setBanner(banner, failed.note_ar || STRINGS.analyzeFailedHint);

  const retry = document.createElement("button");
  retry.className = "btn btn-secondary";
  retry.type = "button";
  retry.textContent = STRINGS.reanalyze;
  retry.addEventListener("click", onRetry);
  banner.appendChild(retry);
}
