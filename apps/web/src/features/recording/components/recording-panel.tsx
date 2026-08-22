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
      <div className="mx-auto my-8 max-w-[680px] overflow-hidden rounded-[28px] border border-[var(--color-line)] bg-[var(--color-surface)] shadow-[var(--shadow-card)]">
        <div className="border-b border-[var(--color-line-soft)] px-6 py-5 sm:px-10">
          <span className="mb-2 inline-flex items-center gap-2 rounded-full bg-[var(--color-danger-soft)] px-3 py-1 text-xs font-bold text-[var(--color-danger)]">
            <span className={cn("h-2 w-2 rounded-full bg-[var(--color-danger)]", !paused && "animate-pulse")} />
            {paused ? strings.pause : "تسجيل مباشر"}
          </span>
          <h2 id="rec-panel-title" className="m-0 text-[26px] font-bold">
            {labels.title}
          </h2>
        </div>
        <div className="px-6 py-10 sm:px-10">
          <LevelDisc discRef={levelMeter.discRef} paused={paused} />
          <RecTimer elapsedSeconds={timer.elapsedSeconds} />
          <p className="mt-1 mb-8 text-sm text-[var(--color-ink-soft)]">
            {paused ? "التسجيل متوقف مؤقتًا ويمكنك استئنافه" : "نتابع مستوى الصوت ونحفظ التسجيل داخل المتصفح"}
          </p>
          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <button
              type="button"
              onClick={paused ? recorder.resume : recorder.pause}
              disabled={stopping}
              className={cn(
                "inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-[var(--radius)] border bg-[var(--color-surface)] px-6 py-3 text-base font-semibold transition-[background,border-color,transform] duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
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
              className="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-[var(--radius)] border border-transparent bg-[var(--color-accent)] px-6 py-3 text-base font-semibold text-white transition-[background,transform] duration-150 hover:bg-[var(--color-accent-dark)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
            >
              <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4">
                <use href="#icon-stop" />
              </svg>
              <span>{labels.stop}</span>
            </button>
          </div>
          {stopping ? (
            <p role="status" className="mt-5 mb-0 text-sm text-[var(--color-ink-soft)]">
              {labels.savingHint}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
