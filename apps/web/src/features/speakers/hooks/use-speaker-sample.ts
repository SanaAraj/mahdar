import { useEffect, useRef, useState } from "react";

import { getAudioUrl } from "@/lib/api-client";
import { PREVIEW_SECONDS } from "@/lib/config";
import type { PlayerApi } from "@/features/player/player-context";

export interface UseSpeakerSampleOptions {
  meetingId: string;
  player?: PlayerApi | null;
}

export interface SpeakerSampleController {
  previewingId: string | null;
  playSample: (speakerId: string, firstStart: number) => void;
}

export function useSpeakerSample({
  meetingId,
  player,
}: UseSpeakerSampleOptions): SpeakerSampleController {
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (player) return;
    const el = new Audio();
    el.preload = "metadata";
    el.src = getAudioUrl(meetingId);
    audioRef.current = el;
    return () => {
      el.pause();
      el.removeAttribute("src");
      el.load();
      audioRef.current = null;
    };
  }, [meetingId, player]);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  const playSample = (speakerId: string, firstStart: number): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setPreviewingId(speakerId);

    if (player) {
      const wasPlaying = player.isPlaying;
      const resumeTime = player.currentTime;
      player.seekTo(firstStart);
      player.play();
      timerRef.current = window.setTimeout(() => {
        player.pause();
        if (!wasPlaying) player.seekTo(resumeTime);
        setPreviewingId(null);
        timerRef.current = null;
      }, PREVIEW_SECONDS * 1000);
      return;
    }

    const el = audioRef.current;
    if (!el) {
      setPreviewingId(null);
      return;
    }
    el.currentTime = firstStart;
    el.play().catch(() => {});
    timerRef.current = window.setTimeout(() => {
      el.pause();
      setPreviewingId(null);
      timerRef.current = null;
    }, PREVIEW_SECONDS * 1000);
  };

  return { previewingId, playSample };
}
