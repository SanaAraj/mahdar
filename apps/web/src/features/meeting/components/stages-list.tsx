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
    <ol className="mx-auto w-full max-w-[560px] space-y-2">
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
        "flex min-h-14 items-center gap-3 rounded-[14px] border border-transparent px-3 py-2.5 text-sm text-[var(--color-ink-soft)] transition-colors",
        stage.state === "running" && "border-[var(--color-accent-ring)] bg-[var(--color-accent-soft)] font-medium text-[var(--color-ink)]",
        stage.state === "done" && "bg-[var(--color-bg)] text-[var(--color-accent)]",
        stage.state === "error" && "border-[var(--color-danger)] bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
      )}
    >
      <StageIcon state={stage.state} />
      <span className="flex-1">{stage.label_ar}</span>
      {stage.key === "diarize" && stage.state === "running" ? (
        <span className="hidden max-w-[210px] text-xs font-normal text-[var(--color-ink-soft)] sm:block">
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
