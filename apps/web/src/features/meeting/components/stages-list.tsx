import { Badge } from "@/components/ui/badge";
import type { Stage, StageState } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

interface StagesListProps {
  stages: Stage[];
}

const STATE_LABEL: Record<StageState, string> = {
  pending: strings.stagePending,
  running: strings.stageRunning,
  done: strings.stageDone,
  skipped: strings.stageSkipped,
  error: strings.stageError,
};

const STATE_BADGE_VARIANT: Record<
  StageState,
  "secondary" | "default" | "success" | "outline" | "danger"
> = {
  pending: "outline",
  running: "default",
  done: "success",
  skipped: "secondary",
  error: "danger",
};

export function StagesList({ stages }: Readonly<StagesListProps>) {
  if (!stages.length) return null;
  return (
    <ol className="mx-auto w-full max-w-[420px] space-y-1">
      {stages.map((stage) => (
        <StageRow key={stage.key} stage={stage} />
      ))}
    </ol>
  );
}

function StageRow({ stage }: Readonly<{ stage: Stage }>) {
  return (
    <li
      data-state={stage.state}
      className={cn(
        "flex items-center gap-3 py-1.5 text-sm text-[var(--color-ink-soft)]",
        stage.state === "running" && "font-medium text-[var(--color-ink)]",
        stage.state === "done" && "text-[var(--color-accent)]",
        stage.state === "error" && "text-[var(--color-danger)]",
      )}
    >
      <StageIcon state={stage.state} />
      <span className="flex-1">{stage.label_ar}</span>
      {stage.key === "diarize" && stage.state === "running" ? (
        <span className="text-xs font-normal text-[var(--color-ink-soft)]">
          {strings.diarizeRunningNote}
        </span>
      ) : null}
      <Badge variant={STATE_BADGE_VARIANT[stage.state]}>{STATE_LABEL[stage.state]}</Badge>
    </li>
  );
}

function StageIcon({ state }: Readonly<{ state: StageState }>) {
  if (state === "running") {
    return (
      <svg className="h-5 w-5 shrink-0 animate-spin" viewBox="0 0 20 20" aria-hidden="true">
        <circle
          cx="10"
          cy="10"
          r="8"
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="2"
          strokeDasharray="30 20"
        />
      </svg>
    );
  }
  if (state === "done") {
    return (
      <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" aria-hidden="true">
        <circle
          cx="10"
          cy="10"
          r="8"
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="2"
        />
        <path d="M6 10l3 3 5-6" fill="none" stroke="var(--color-accent)" strokeWidth="2" />
      </svg>
    );
  }
  if (state === "error") {
    return (
      <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" aria-hidden="true">
        <circle
          cx="10"
          cy="10"
          r="8"
          fill="none"
          stroke="var(--color-danger)"
          strokeWidth="2"
        />
        <path d="M7 7l6 6M13 7l-6 6" stroke="var(--color-danger)" strokeWidth="2" />
      </svg>
    );
  }
  if (state === "skipped") {
    return (
      <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" aria-hidden="true">
        <circle
          cx="10"
          cy="10"
          r="8"
          fill="none"
          stroke="var(--color-line)"
          strokeWidth="2"
          strokeDasharray="3 3"
        />
      </svg>
    );
  }
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="8" fill="none" stroke="var(--color-line)" strokeWidth="2" />
    </svg>
  );
}
