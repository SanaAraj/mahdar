import { useEffect, useRef, type RefObject } from "react";

import { ANALYSER_FFT_SIZE, LEVEL_SENSITIVITY } from "@/lib/config";

export interface UseLevelMeterOptions {
  stream: MediaStream | null;
  onLevel?: (level: number) => void;
}

export interface UseLevelMeterResult {
  discRef: RefObject<HTMLDivElement | null>;
}

export const PULSE_BASE = 0.9;
export const PULSE_RANGE = 0.45;

export function useLevelMeter({
  stream,
  onLevel,
}: UseLevelMeterOptions): UseLevelMeterResult {
  const discRef = useRef<HTMLDivElement | null>(null);
  const onLevelRef = useRef(onLevel);

  useEffect(() => {
    onLevelRef.current = onLevel;
  }, [onLevel]);

  useEffect(() => {
    if (!stream) return;
    const Ctor =
      window.AudioContext ??
      (window as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    const audioContext = new Ctor();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = ANALYSER_FFT_SIZE;
    source.connect(analyser);
    const data = new Float32Array(analyser.fftSize);
    let rafId = 0;
    const tick = () => {
      analyser.getFloatTimeDomainData(data);
      let sum = 0;
      for (const v of data) sum += v * v;
      const rms = Math.sqrt(sum / data.length);
      const level = Math.min(1, rms * LEVEL_SENSITIVITY);
      onLevelRef.current?.(level);
      const el = discRef.current;
      if (el) {
        el.style.setProperty("--pulse", (PULSE_BASE + level * PULSE_RANGE).toFixed(3));
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(rafId);
      source.disconnect();
      void audioContext.close().catch(() => undefined);
    };
  }, [stream]);

  return { discRef };
}
