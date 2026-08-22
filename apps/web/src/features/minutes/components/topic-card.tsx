import type { Topic } from "@/lib/schemas";
import { CitationChips } from "./citation-chips";

interface TopicCardProps {
  topic: Topic;
  startSeconds: Readonly<Record<string, number>>;
  onSeek: (sentenceId: string) => unknown;
}

export function TopicCard({ topic, startSeconds, onSeek }: TopicCardProps) {
  return (
    <li className="rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-surface)] p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <strong className="text-sm">{topic.title}</strong>
        <CitationChips segmentIds={topic.segment_ids} startSeconds={startSeconds} onSeek={onSeek} />
      </div>
      {topic.summary ? (
        <p className="m-0 mt-1 text-sm leading-relaxed text-[var(--color-ink-soft)]">{topic.summary}</p>
      ) : null}
    </li>
  );
}
