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
  const accumulatedMsRef = useRef(0);
  const startedAtRef = useRef<number | null>(null);
  const wasRunningRef = useRef(false);

  const clear = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    accumulatedMsRef.current = 0;
    startedAtRef.current = null;
    setElapsedSeconds(0);
  }, []);

  useEffect(() => {
    if (running && !wasRunningRef.current) reset();
    wasRunningRef.current = running;
    if (!running) {
      clear();
      startedAtRef.current = null;
      return;
    }

    if (paused) {
      if (startedAtRef.current !== null) {
        accumulatedMsRef.current += Date.now() - startedAtRef.current;
        startedAtRef.current = null;
      }
      clear();
      setElapsedSeconds(Math.floor(accumulatedMsRef.current / 1000));
      return;
    }

    startedAtRef.current = Date.now();
    intervalRef.current = window.setInterval(() => {
      const activeMs = startedAtRef.current === null ? 0 : Date.now() - startedAtRef.current;
      setElapsedSeconds(Math.floor((accumulatedMsRef.current + activeMs) / 1000));
    }, TIMER_TICK_MS);
    return () => {
      clear();
      if (startedAtRef.current !== null) {
        accumulatedMsRef.current += Date.now() - startedAtRef.current;
        startedAtRef.current = null;
      }
    };
  }, [running, paused, clear, reset]);

  return { elapsedSeconds, reset };
}
