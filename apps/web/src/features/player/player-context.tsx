import { createContext, useCallback, useContext, useMemo, useRef } from "react";

import { getAudioUrl } from "@/lib/api-client";
import { strings } from "@/lib/strings";
import type { Sentence } from "@/lib/schemas";

import { useAudioPlayer } from "./hooks/use-player";

export interface PlayerApi {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  errorAr: string | null;
  toggle: () => void;
  seekTo: (t: number) => void;
  play: () => void;
  pause: () => void;
  seekToSentence: (id: string) => boolean;
}

const PlayerContext = createContext<PlayerApi | null>(null);

export interface PlayerProviderProps {
  meetingId: string;
  sentences: Sentence[];
  children: React.ReactNode;
}

export function PlayerProvider({ meetingId, sentences, children }: PlayerProviderProps) {
  const player = useAudioPlayer(getAudioUrl(meetingId), strings.audioFailed);
  const sentencesRef = useRef<Sentence[]>(sentences);
  sentencesRef.current = sentences;

  const seekToSentence = useCallback(
    (id: string): boolean => {
      const match = sentencesRef.current.find((s) => s.id === id);
      if (!match) return false;
      player.seekTo(match.start);
      player.play();
      return true;
    },
    [player.seekTo, player.play],
  );

  const api = useMemo<PlayerApi>(
    () => ({
      isPlaying: player.isPlaying,
      currentTime: player.currentTime,
      duration: player.duration,
      errorAr: player.errorAr,
      toggle: player.toggle,
      seekTo: player.seekTo,
      play: player.play,
      pause: player.pause,
      seekToSentence,
    }),
    [player, seekToSentence],
  );

  return <PlayerContext.Provider value={api}>{children}</PlayerContext.Provider>;
}

export function usePlayer(): PlayerApi {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used inside PlayerProvider");
  return ctx;
}
