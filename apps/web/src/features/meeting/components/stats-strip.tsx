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
    { label: strings.durationLabel, value: job.duration_s != null ? formatDuration(job.duration_s) : "—" },
    { label: strings.attendeesLabel, value: job.speakers.length ? speakerCount(job.speakers.length) : "—" },
    { label: strings.transcriptHeading, value: sentencesCount(job.sentences.length) },
    { label: strings.followupTasks, value: String(analysis.tasks.length) },
  ];
  return (
    <div className="mb-5 grid grid-cols-2 overflow-hidden rounded-[12px] border border-[var(--color-line)] bg-[var(--color-surface)] sm:grid-cols-4">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className="flex min-h-[82px] flex-col items-start justify-center gap-0.5 border-b border-l border-[var(--color-line-soft)] px-4 py-3 text-start last:border-l-0 sm:border-b-0"
        >
          <span className="text-lg font-bold tabular-nums text-[var(--color-ink)]">
            {tile.value}
          </span>
          <span className="text-xs font-medium text-[var(--color-ink-soft)]">{tile.label}</span>
        </div>
      ))}
    </div>
  );
}
