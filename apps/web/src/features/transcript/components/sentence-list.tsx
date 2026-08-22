import { useMemo } from "react";

import type { MeetingJob, Speaker } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import { groupSentenceRuns } from "../utils/sentence-grouping";
import { SentenceRow } from "./sentence-row";

interface SentenceListProps {
  job: MeetingJob;
  onSeek: (sentenceId: string) => unknown;
  activeSentenceId?: string;
}

export function SentenceList({ job, onSeek, activeSentenceId }: SentenceListProps) {
  const runs = useMemo(() => groupSentenceRuns(job.sentences), [job.sentences]);
  const speakersById = useMemo(
    () => new Map(job.speakers.map((speaker) => [speaker.id, speaker])),
    [job.speakers],
  );

  if (runs.length === 0) {
    return <p className="m-0 text-sm text-[var(--color-ink-soft)]">{strings.sectionsEmpty}</p>;
  }

  return (
    <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
      {runs.flatMap((run) =>
        run.sentences.map((sentence, index) => {
          const speaker: Speaker | undefined =
            index === 0 && run.speakerId != null ? speakersById.get(run.speakerId) : undefined;
          return (
            <SentenceRow
              key={sentence.id}
              sentence={sentence}
              speaker={speaker}
              onSeek={onSeek}
              active={sentence.id === activeSentenceId}
            />
          );
        }),
      )}
    </ul>
  );
}
