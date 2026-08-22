import { formatClock } from "@/lib/format";

interface CitationChipsProps {
  segmentIds: string[];
  startSeconds: Readonly<Record<string, number>>;
  onSeek: (sentenceId: string) => unknown;
}

export function CitationChips({ segmentIds, startSeconds, onSeek }: CitationChipsProps) {
  const known = segmentIds.filter((id) => startSeconds[id] != null);
  if (known.length === 0) return null;

  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {known.map((id) => (
        <button
          key={id}
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onSeek(id);
          }}
          className="cursor-pointer rounded-full border border-[var(--color-line)] bg-[var(--color-surface)] px-2 py-0.5 text-[11px] text-[var(--color-ink-soft)] tabular-nums transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-accent-dark)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
        >
          <bdi>{formatClock(startSeconds[id])}</bdi>
        </button>
      ))}
    </span>
  );
}
