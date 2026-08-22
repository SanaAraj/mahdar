import { createContext, useCallback, useContext, useEffect, useMemo, useRef } from "react";

import { getAudioUrl } from "@/lib/api-client";
import { strings } from "@/lib/strings";
import type { Sentence } from "@/lib/schemas";

import { useAudioPlayer } from "./hooks/use-player";

export interface PlayerApi {
  isReady: boolean;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  errorAr: string | null;
  toggle: () => void;
  seekTo: (t: number) => void;
  play: () => void;
  pause: () => void;
  reload: () => void;
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
  const { play, seekTo } = player;

  useEffect(() => {
    sentencesRef.current = sentences;
  }, [sentences]);

  const seekToSentence = useCallback(
    (id: string): boolean => {
      const match = sentencesRef.current.find((s) => s.id === id);
      if (!match) return false;
      seekTo(match.start);
      play();
      return true;
    },
    [play, seekTo],
  );

  const api = useMemo<PlayerApi>(
    () => ({
      isReady: player.isReady,
      isPlaying: player.isPlaying,
      currentTime: player.currentTime,
      duration: player.duration,
      errorAr: player.errorAr,
      toggle: player.toggle,
      seekTo: player.seekTo,
      play: player.play,
      pause: player.pause,
      reload: player.reload,
      seekToSentence,
    }),
    [
      player.currentTime,
      player.duration,
      player.errorAr,
      player.isPlaying,
      player.isReady,
      player.pause,
      player.play,
      player.reload,
      player.seekTo,
      player.toggle,
      seekToSentence,
    ],
  );

  return <PlayerContext.Provider value={api}>{children}</PlayerContext.Provider>;
}

export function usePlayer(): PlayerApi {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used inside PlayerProvider");
  return ctx;
}
