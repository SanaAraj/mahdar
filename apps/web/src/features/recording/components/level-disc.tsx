import type { RefObject } from "react";

import { cn } from "@/lib/utils";

export interface LevelDiscProps {
  discRef: RefObject<HTMLDivElement | null>;
  paused: boolean;
  className?: string;
}

export function LevelDisc({ discRef, paused, className }: LevelDiscProps) {
  return (
    <div className="py-6" aria-hidden="true">
      <div
        ref={discRef}
        className={cn(
          "mx-auto mb-6 h-[120px] w-[120px] scale-[var(--pulse,1)] rounded-full bg-[var(--color-accent)] shadow-[0_0_0_var(--record-halo)_var(--color-accent-ring)] transition-transform duration-[120ms] ease-linear",
          paused && "border-2 border-[var(--color-line)] bg-[var(--color-surface)] shadow-none",
          className,
        )}
      />
    </div>
  );
}
