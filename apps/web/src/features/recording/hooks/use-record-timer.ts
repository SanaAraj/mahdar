import { useCallback, useEffect, useRef, useState } from "react";

import { TIMER_TICK_MS } from "@/lib/config";

export interface UseRecordTimerOptions {
  running: boolean;
  paused: boolean;
}

export interface UseRecordTimerResult {
  elapsedSeconds: number;
  reset: () => void;
}

export function useRecordTimer({ running, paused }: UseRecordTimerOptions): UseRecordTimerResult {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const intervalRef = useRef<number | null>(null);

  const clear = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    setElapsedSeconds(0);
  }, []);

  useEffect(() => {
    if (!running) {
      clear();
      return;
    }
    setElapsedSeconds(0);
    intervalRef.current = window.setInterval(() => {
      if (!paused) setElapsedSeconds((s) => s + 1);
    }, TIMER_TICK_MS);
    return clear;
  }, [running, paused, clear]);

  return { elapsedSeconds, reset };
}
