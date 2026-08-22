import { cn } from "@/lib/utils";
import type { Speaker } from "@/lib/schemas";

import { speakerColorFor } from "../utils/palette";

export interface SpeakerTagProps {
  speaker: Pick<Speaker, "id" | "label">;
  className?: string;
}

export function SpeakerTag({ speaker, className }: SpeakerTagProps) {
  const color = speakerColorFor(speaker.id);
  return (
    <span
      className={cn(
        "inline-block shrink-0 rounded-md px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
        className,
      )}
      style={{ background: color.bg, color: color.ink }}
    >
      {speaker.label}
    </span>
  );
}
