// The minutes section: topics as title-and-summary cards; decisions and
// directives only appear when the model actually extracted any. Every text
// value goes in via textContent, never innerHTML.

import { STRINGS } from "./strings.js";
import { setBanner } from "./views.js";

const $ = (id) => document.getElementById(id);

function emptyNote(text) {
  const p = document.createElement("p");
  p.className = "note-empty";
  p.textContent = text;
  return p;
}

export function renderMinutes(job) {
  const section = $("minutes-section");
  section.innerHTML = "";
  const analysis = job.analysis;
  if (!analysis) {
    section.appendChild(emptyNote(STRINGS.sectionsEmpty));
    return;
  }
  section.appendChild(buildTopicsList(analysis.topics));
  for (const list of buildPlainLists(analysis)) {
    section.appendChild(list);
  }
}

function buildTopicsList(topics) {
  const wrap = document.createElement("div");
  wrap.className = "minutes-group";
  if (!topics.length) {
    wrap.appendChild(emptyNote(STRINGS.sectionsEmpty));
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
    ul.appendChild(li);
  }
  wrap.appendChild(ul);
  return wrap;
}

// Decisions and directives stack under the topics cards; both use the same
// flat item style to keep the two groups visually distinct from the cards.
function buildPlainLists(analysis) {
  const groups = [];
  for (const items of [analysis.decisions, analysis.directives]) {
    if (!items.length) continue;
    const ul = document.createElement("ul");
    ul.className = "minutes-plain";
    for (const item of items) {
      const li = document.createElement("li");
      const span = document.createElement("span");
      span.textContent = item.text;
      li.appendChild(span);
      ul.appendChild(li);
    }
    groups.push(ul);
  }
  return groups;
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
