import { iconHref } from "@/components/icon-sprite";
import { formatClock } from "@/lib/format";
import { strings } from "@/lib/strings";
import type { Sentence } from "@/lib/schemas";

import { usePlayer } from "../player-context";
import { TickStrip } from "./tick-strip";

export interface SkimBarProps {
  sentences: Sentence[];
}

export function SkimBar({ sentences }: SkimBarProps) {
  const { isPlaying, currentTime, duration, errorAr, toggle, seekToSentence } = usePlayer();

  if (duration <= 0) return null;

  return (
    <div
      dir="rtl"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--color-line)] bg-[var(--color-surface)]/95 backdrop-blur-sm"
      style={{ boxShadow: "0 -2px 12px rgba(29, 29, 27, 0.06)" }}
    >
      <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
        <button
          type="button"
          onClick={toggle}
          aria-label={isPlaying ? strings.pause : strings.play}
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-0 bg-[var(--color-accent)] p-0 text-white transition-colors hover:bg-[var(--color-accent-dark)] active:scale-95"
        >
          <svg width="16" height="16" aria-hidden="true" className="fill-current">
            <use href={iconHref(isPlaying ? "pause" : "play")} />
          </svg>
        </button>

        <TickStrip
          sentences={sentences}
          currentTime={currentTime}
          duration={duration}
          onSeekSentence={seekToSentence}
        />

        <span dir="ltr" className="shrink-0 tabular-nums text-sm text-[var(--color-ink)]">
          {formatClock(currentTime)} / {formatClock(duration)}
        </span>
      </div>

      {errorAr ? (
        <div role="alert" className="bg-[var(--color-danger-soft)] px-4 py-1 text-center text-xs text-[var(--color-danger)]">
          {errorAr}
        </div>
      ) : null}
    </div>
  );
}
