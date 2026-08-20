// Stats strip above the result: counts of the three mined item kinds.
// Tiles render in the reference's visual order (topics, decisions, tasks);
// on the RTL grid the first child anchors to the inline-start (right) edge.

import { STRINGS } from "./strings.js";

const $ = (id) => document.getElementById(id);

export function renderStats(job) {
  const strip = $("stats");
  strip.innerHTML = "";
  const analysis = job.analysis;
  // No analysis (or all-counts anchor on the strip) leaves no dead grid gap.
  // The empty-stats section starts hidden in the HTML; revealing here keeps
  // the DOM in sync with what the job actually carries.
  if (!analysis) return;
  strip.hidden = false;
  const tiles = [
    [STRINGS.topicsHeading, analysis.topics.length],
    [STRINGS.decisionLabel, analysis.decisions.length],
    [STRINGS.followupTasks, analysis.tasks.length],
  ];
  for (const [label, count] of tiles) {
    strip.appendChild(buildTile(label, count));
  }
}

function buildTile(label, count) {
  const tile = document.createElement("div");
  tile.className = "stat-tile";
  const value = document.createElement("span");
  value.className = "stat-value";
  value.textContent = `${count}`;
  const name = document.createElement("span");
  name.className = "stat-label";
  name.textContent = label;
  tile.append(value, name);
  return tile;
}
