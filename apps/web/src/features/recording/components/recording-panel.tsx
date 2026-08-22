import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

import { LevelDisc } from "./level-disc";
import { RecTimer } from "./rec-timer";
import type { useLevelMeter } from "../hooks/use-level-meter";
import type { useRecorder } from "../hooks/use-recorder";
import type { useRecordTimer } from "../hooks/use-record-timer";

export interface RecordingPanelLabels {
  title: string;
  stop: string;
  savingHint: string;
}

export interface RecordingPanelProps {
  labels: RecordingPanelLabels;
  recorder: ReturnType<typeof useRecorder>;
  levelMeter: ReturnType<typeof useLevelMeter>;
  timer: ReturnType<typeof useRecordTimer>;
  onStop: () => void;
}

export function RecordingPanel({
  labels,
  recorder,
  levelMeter,
  timer,
  onStop,
}: RecordingPanelProps) {
  const paused = recorder.state === "paused";
  const stopping = recorder.state === "stopping";
  const pauseIcon = paused ? "#icon-play" : "#icon-pause";
  const pauseLabel = paused ? strings.resume : strings.pause;
  return (
    <section aria-labelledby="rec-panel-title" className="text-center">
      <div className="mx-auto my-12 max-w-[var(--width-stage)] rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-surface)] px-6 py-10 shadow-[var(--shadow-card)] sm:px-10 sm:py-12">
        <h2 id="rec-panel-title" className="m-0 mb-2 text-[22px] font-semibold">
          {labels.title}
        </h2>
        <LevelDisc discRef={levelMeter.discRef} paused={paused} />
        <RecTimer elapsedSeconds={timer.elapsedSeconds} />
        <div className="flex justify-center gap-4">
          <button
            type="button"
            onClick={paused ? recorder.resume : recorder.pause}
            disabled={stopping}
            className={cn(
              "inline-flex cursor-pointer items-center gap-2 rounded-[var(--radius)] border bg-[var(--color-surface)] px-5 py-2.5 text-base font-semibold transition-[background,border-color,transform] duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
              paused
                ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-dark)]"
                : "border-[var(--color-line)] text-[var(--color-ink)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent-dark)]",
            )}
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4">
              <use href={pauseIcon} />
            </svg>
            <span>{pauseLabel}</span>
          </button>
          <button
            type="button"
            onClick={onStop}
            disabled={stopping}
            className="inline-flex cursor-pointer items-center gap-2 rounded-[var(--radius)] border border-transparent bg-[var(--color-accent)] px-5 py-2.5 text-base font-semibold text-white transition-[background,transform] duration-150 hover:bg-[var(--color-accent-dark)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4">
              <use href="#icon-stop" />
            </svg>
            <span>{labels.stop}</span>
          </button>
        </div>
        {stopping ? (
          <p role="status" className="mt-4 mb-0 text-sm text-[var(--color-ink-soft)]">
            {labels.savingHint}
          </p>
        ) : null}
      </div>
    </section>
  );
}
