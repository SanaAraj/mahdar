import { formatClock, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface RecTimerProps {
  elapsedSeconds: number;
  className?: string;
}

export function RecTimer({ elapsedSeconds, className }: RecTimerProps) {
  const text =
    elapsedSeconds >= 3600 ? formatDuration(elapsedSeconds) : formatClock(elapsedSeconds);
  return (
    <p
      className={cn(
        "m-0 mb-6 text-[32px] font-semibold text-[var(--color-ink)] [font-variant-numeric:tabular-nums]",
        className,
      )}
    >
      {text}
    </p>
  );
}
