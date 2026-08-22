import { formatDuration } from "@/lib/format";
import type { MeetingJob } from "@/lib/schemas";
import { sentencesCount, speakerCount, strings } from "@/lib/strings";

interface StatsStripProps {
  job: MeetingJob;
}

export function StatsStrip({ job }: Readonly<StatsStripProps>) {
  const analysis = job.analysis;
  if (!analysis) return null;
  const tiles: Array<{ label: string; value: string }> = [
    { label: strings.topicsHeading, value: String(analysis.topics.length) },
    { label: strings.decisionLabel, value: String(analysis.decisions.length) },
    { label: strings.followupTasks, value: String(analysis.tasks.length) },
    { label: strings.transcriptHeading, value: sentencesCount(job.sentences.length) },
  ];
  if (job.speakers.length) {
    tiles.push({ label: strings.attendeesLabel, value: speakerCount(job.speakers.length) });
  }
  if (job.duration_s != null) {
    tiles.push({ label: strings.durationLabel, value: formatDuration(job.duration_s) });
  }
  return (
    <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className="flex flex-col items-center justify-center gap-1 rounded-[var(--radius)] border border-[var(--color-line)] bg-[var(--color-surface)] px-3 py-4 text-center shadow-[var(--shadow-card)]"
        >
          <span className="text-2xl font-bold tabular-nums text-[var(--color-accent)]">
            {tile.value}
          </span>
          <span className="text-xs text-[var(--color-ink-soft)]">{tile.label}</span>
        </div>
      ))}
    </div>
  );
}
