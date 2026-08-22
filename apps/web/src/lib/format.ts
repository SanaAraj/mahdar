import { speakerCount, strings } from "./strings";
import type { MeetingJob } from "./schemas";

export function formatClock(totalSeconds: number): string {
  const total = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : formatClock(total);
}

export function metaLine(job: MeetingJob): string {
  const parts: string[] = [];
  if (job.date_gregorian) parts.push(job.date_gregorian);
  if (job.date_hijri) parts.push(`${job.date_hijri} ${strings.hijriSuffix.trim()}`);
  if (job.duration_s != null) parts.push(`${strings.durationLabel}: ${formatDuration(job.duration_s)}`);
  if (job.speakers.length) parts.push(speakerCount(job.speakers.length));
  return parts.join(" · ");
}
