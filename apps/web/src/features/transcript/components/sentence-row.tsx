import type { Sentence, Speaker } from "@/lib/schemas";
import { formatClock } from "@/lib/format";
import { SpeakerTag } from "@/features/speakers";

interface SentenceRowProps {
  sentence: Sentence;
  speaker?: Speaker;
  onSeek: (sentenceId: string) => unknown;
  active?: boolean;
}

export function SentenceRow({ sentence, speaker, onSeek, active = false }: SentenceRowProps) {
  function activate(): void {
    onSeek(sentence.id);
  }

  return (
    <li
      data-sid={sentence.id}
      tabIndex={0}
      onClick={activate}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      }}
      className={
        active
          ? "group flex cursor-pointer items-center gap-2 rounded-[var(--radius-lg)] px-2 py-2.5 transition-colors bg-[var(--color-accent-soft)] shadow-[inset_-2px_0_0_var(--color-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
          : "group flex cursor-pointer items-center gap-2 rounded-[var(--radius-lg)] px-2 py-2.5 transition-colors hover:bg-[var(--color-accent-soft)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
      }
    >
      <span className="inline-flex shrink-0 items-center gap-1.5">
        <span className="rounded-[6px] bg-[var(--color-time-bg)] px-2 py-0.5 text-xs whitespace-nowrap text-[var(--color-ink-soft)] tabular-nums">
          <bdi>{formatClock(sentence.start)}</bdi>
        </span>
        <svg
          viewBox="0 0 16 16"
          aria-hidden="true"
          className="h-3 w-3 shrink-0 text-[var(--color-accent)] opacity-0 group-hover:opacity-100"
        >
          <use href="#i-play" />
        </svg>
      </span>
      {speaker ? <SpeakerTag speaker={speaker} /> : null}
      <p className="m-0 text-[15px]">{sentence.text}</p>
    </li>
  );
}
