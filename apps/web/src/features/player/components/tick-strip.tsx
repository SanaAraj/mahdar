import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { speakerColor } from "@/lib/config";
import type { Sentence } from "@/lib/schemas";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";

const NEUTRAL_TICK = "#e3e1d9";

export interface TickStripProps {
  sentences: Sentence[];
  currentTime: number;
  duration: number;
  onSeekSentence: (id: string) => void;
}

export function TickStrip({ sentences, currentTime, duration, onSeekSentence }: TickStripProps) {
  const safeDuration = duration > 0 ? duration : 1;

  return (
    <TooltipProvider delayDuration={150}>
      <div
        className="flex h-10 min-w-0 flex-1 items-center gap-[2px]"
        role="group"
        aria-label="sentence ticks"
        dir="ltr"
      >
        {sentences.map((sentence) => {
          const color = sentence.speaker ? speakerColor(sentence.speaker).ring : NEUTRAL_TICK;
          const widthPct = Math.max(((sentence.end - sentence.start) / safeDuration) * 100, 0.4);
          const isPast = sentence.start <= currentTime;
          return (
            <Tooltip key={sentence.id}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label={`${formatClock(sentence.start)} · ${sentence.text.slice(0, 40)}`}
                  onClick={() => onSeekSentence(sentence.id)}
                  className="flex h-full min-w-[2px] items-end border-0 bg-transparent p-0"
                  style={{ flexGrow: widthPct, flexBasis: 0 }}
                >
                  <span
                    className={cn(
                      "block h-[30px] w-full rounded-[2px] transition-colors duration-150",
                      isPast ? "" : "opacity-40",
                    )}
                    style={{ background: color }}
                  />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <span dir="rtl">{sentence.text}</span>
                <span className="ms-1 tabular-nums" dir="ltr">
                  {formatClock(sentence.start)}
                </span>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
