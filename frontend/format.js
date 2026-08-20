// The single mm:ss clock used by the recorder timer and the transcript rows.
export function formatClock(totalSeconds) {
  const m = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// Hours-aware duration for the meeting meta line (design shows h:mm:ss when needed).
export function formatDuration(seconds) {
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : formatClock(total);
}

// Gregorian date, then Hijri, then duration, then speaker count.
export function metaLine(job, strings) {
  const parts = [];
  if (job.date_gregorian) parts.push(job.date_gregorian);
  if (job.date_hijri) parts.push(`${job.date_hijri} ${strings.hijriSuffix.trim()}`);
  if (job.duration_s != null) parts.push(`${strings.durationLabel}: ${formatDuration(job.duration_s)}`);
  if (job.speakers.length) parts.push(strings.speakerCount(job.speakers.length));
  return parts.join(" · ");
}
