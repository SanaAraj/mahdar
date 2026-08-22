import type { CSSProperties } from "react";

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
  const {
    isReady,
    isPlaying,
    currentTime,
    duration,
    errorAr,
    toggle,
    seekTo,
    reload,
    seekToSentence,
  } = usePlayer();
  const safeDuration = duration > 0 ? duration : 1;

  return (
    <section
      dir="rtl"
      aria-labelledby="audio-player-title"
      className="sticky top-3 z-30 mb-5 overflow-hidden rounded-[12px] border border-[var(--color-line)] bg-[var(--color-surface)]/95 shadow-[var(--shadow)] backdrop-blur-md"
    >
      <div className="flex items-center justify-between gap-3 border-b border-[var(--color-line-soft)] px-4 py-3 sm:px-5">
        <div>
          <h3 id="audio-player-title" className="m-0 text-base font-bold">
            {strings.audioHeading}
          </h3>
          <p className="m-0 text-xs text-[var(--color-ink-soft)]">
            {isReady ? strings.audioReady : strings.audioLoading}
          </p>
        </div>
        <span dir="ltr" className="shrink-0 tabular-nums text-sm font-semibold text-[var(--color-ink)]">
          {formatClock(currentTime)} / {duration > 0 ? formatClock(duration) : "--:--"}
        </span>
      </div>
      <div className="flex items-center gap-3 px-4 py-3 sm:px-5">
        <button
          type="button"
          onClick={toggle}
          aria-label={isPlaying ? strings.pause : strings.play}
          disabled={!isReady}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-0 bg-[var(--color-accent)] p-0 text-white transition-[background,transform] hover:bg-[var(--color-accent-dark)] active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg width="18" height="18" aria-hidden="true" className="fill-current">
            <use href={iconHref(isPlaying ? "pause" : "play")} />
          </svg>
        </button>
        <div className="min-w-0 flex-1">
          <input
            type="range"
            min={0}
            max={safeDuration}
            step={0.1}
            value={Math.min(currentTime, safeDuration)}
            disabled={!isReady}
            aria-label={strings.audioSeek}
            onChange={(event) => seekTo(Number(event.target.value))}
            className="audio-range block w-full"
            style={{ "--audio-progress": `${(currentTime / safeDuration) * 100}%` } as CSSProperties}
          />
          <TickStrip
            sentences={sentences}
            currentTime={currentTime}
            duration={duration}
            onSeekSentence={seekToSentence}
          />
        </div>
      </div>

      {errorAr ? (
        <div role="alert" className="flex items-center justify-between gap-3 bg-[var(--color-danger-soft)] px-4 py-2 text-xs text-[var(--color-danger)] sm:px-5">
          <span>{errorAr}</span>
          <button type="button" onClick={reload} className="cursor-pointer font-bold underline underline-offset-2">
            {strings.audioRetry}
          </button>
        </div>
      ) : null}
    </section>
  );
}
