import { useMemo, useState } from "react";

import type { Sentence, Speaker } from "@/lib/schemas";
import type { PlayerApi } from "@/features/player/player-context";

import { useRenameSpeakers, type RenameInput } from "../hooks/use-rename-speakers";
import { useSpeakerSample } from "../hooks/use-speaker-sample";
import { SpeakerChip, extractRenameErrorAr } from "./speaker-chip";

export interface SpeakersBarProps {
  meetingId: string;
  speakers: Speaker[];
  sentences?: Sentence[];
  player?: PlayerApi | null;
  onSpeakerSelected?: (speaker: Speaker) => void;
  onSpeakersChanged?: () => void;
}

export function SpeakersBar({
  meetingId,
  speakers,
  sentences,
  player,
  onSpeakerSelected,
  onSpeakersChanged,
}: SpeakersBarProps) {
  const renameMutation = useRenameSpeakers(meetingId);
  const { previewingId, playSample } = useSpeakerSample({ meetingId, player });
  const [renameErrorAr, setRenameErrorAr] = useState<string | null>(null);
  const [errorSpeakerId, setErrorSpeakerId] = useState<string | null>(null);

  const segmentCounts = useMemo(() => {
    const map = new Map<string, number>();
    if (!sentences) return map;
    for (const s of sentences) {
      if (!s.speaker) continue;
      map.set(s.speaker, (map.get(s.speaker) ?? 0) + 1);
    }
    return map;
  }, [sentences]);

  if (!speakers || speakers.length === 0) return null;

  const handleRename = (input: RenameInput): void => {
    setRenameErrorAr(null);
    setErrorSpeakerId(input.speakerId);
    renameMutation.mutate(input, {
      onError: (err) => {
        setRenameErrorAr(extractRenameErrorAr(err));
      },
      onSuccess: () => {
        setRenameErrorAr(null);
        setErrorSpeakerId(null);
        onSpeakersChanged?.();
      },
    });
  };

  return (
    <div
      role="group"
      aria-label="speakers"
      className="flex flex-wrap items-center gap-1.5 overflow-x-auto py-1"
    >
      {speakers.map((speaker) => (
        <SpeakerChip
          key={speaker.id}
          speaker={speaker}
          segmentCount={segmentCounts.get(speaker.id)}
          isPreviewing={previewingId === speaker.id}
          isRenaming={renameMutation.isPending}
          renameErrorAr={errorSpeakerId === speaker.id ? renameErrorAr : null}
          onSelect={(s) => {
            onSpeakerSelected?.(s);
          }}
          onSample={(s) => {
            playSample(s.id, s.first_start);
          }}
          onRename={handleRename}
          onRenameDismiss={() => {
            setRenameErrorAr(null);
            setErrorSpeakerId(null);
          }}
        />
      ))}
    </div>
  );
}
