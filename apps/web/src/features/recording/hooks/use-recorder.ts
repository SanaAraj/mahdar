import { useCallback, useEffect, useRef, useState } from "react";

import { MIME_CANDIDATES, RECORD_TICK_MS } from "@/lib/config";
import { strings } from "@/lib/strings";

import { concatChunks } from "../utils/blob-file";

export type RecorderState = "idle" | "recording" | "paused" | "stopping";

export interface UseRecorderResult {
  state: RecorderState;
  isSupported: boolean;
  stream: MediaStream | null;
  start: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => Promise<Blob | null>;
  reset: () => void;
}

function pickMime(): string {
  if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") {
    return "";
  }
  return MIME_CANDIDATES.find((m) => window.MediaRecorder.isTypeSupported(m)) ?? "";
}

function detectSupported(): boolean {
  if (typeof navigator === "undefined" || typeof window === "undefined") return false;
  return Boolean(navigator.mediaDevices?.getUserMedia) && typeof window.MediaRecorder !== "undefined";
}

export function useRecorder(): UseRecorderResult {
  const [state, setState] = useState<RecorderState>("idle");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const isSupported = detectSupported();

  const cleanup = useCallback(() => {
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) track.stop();
      streamRef.current = null;
    }
    setStream(null);
    recorderRef.current = null;
  }, []);

  const start = useCallback(async () => {
    if (!detectSupported()) {
      throw new Error(strings.micUnsupported);
    }
    let micStream: MediaStream;
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      throw new Error(strings.micDenied);
    }
    streamRef.current = micStream;
    setStream(micStream);
    chunksRef.current = [];
    const mime = pickMime();
    const recorder = mime
      ? new MediaRecorder(micStream, { mimeType: mime })
      : new MediaRecorder(micStream);
    recorder.addEventListener("dataavailable", (e: BlobEvent) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    });
    recorderRef.current = recorder;
    recorder.start(RECORD_TICK_MS);
    setState("recording");
  }, []);

  const pause = useCallback(() => {
    const rec = recorderRef.current;
    if (rec && rec.state === "recording") {
      rec.pause();
      setState("paused");
    }
  }, []);

  const resume = useCallback(() => {
    const rec = recorderRef.current;
    if (rec && rec.state === "paused") {
      rec.resume();
      setState("recording");
    }
  }, []);

  const stop = useCallback((): Promise<Blob | null> => {
    const rec = recorderRef.current;
    if (!rec) return Promise.resolve(null);
    setState("stopping");
    const mime = rec.mimeType || "audio/webm";
    return new Promise((resolve) => {
      rec.addEventListener(
        "stop",
        () => {
          const blob = concatChunks(chunksRef.current, mime);
          chunksRef.current = [];
          cleanup();
          setState("idle");
          resolve(blob);
        },
        { once: true },
      );
      rec.stop();
    });
  }, [cleanup]);

  const reset = useCallback(() => {
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") {
      try {
        rec.stop();
      } catch {
        void 0;
      }
    }
    chunksRef.current = [];
    cleanup();
    setState("idle");
  }, [cleanup]);

  useEffect(() => {
    return () => {
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") {
        try {
          rec.stop();
        } catch {
          void 0;
        }
      }
      for (const track of streamRef.current?.getTracks() ?? []) track.stop();
      streamRef.current = null;
      recorderRef.current = null;
      chunksRef.current = [];
    };
  }, []);

  return { state, isSupported, stream, start, pause, resume, stop, reset };
}
