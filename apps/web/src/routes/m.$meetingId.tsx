import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { strings } from "@/lib/strings";
import { useMeetingJob } from "@/features/meeting/hooks/use-meeting-job";
import { isApiError } from "@/lib/api-client";
import { useReanalyze } from "@/features/meeting/hooks/use-reanalyze";
import { StagesList } from "@/features/meeting/components/stages-list";
import { StatsStrip } from "@/features/meeting/components/stats-strip";
import { DoneHeader } from "@/features/meeting/components/done-header";
import { ErrorView } from "@/features/meeting/components/error-view";
import { AnalysisBanner } from "@/features/meeting/components/analysis-banner";
import { PlayerProvider, usePlayer } from "@/features/player/player-context";
import { SkimBar } from "@/features/player/components/skim-bar";
import { SpeakersBar } from "@/features/speakers";
import { SentenceList } from "@/features/transcript";
import { MinutesSections } from "@/features/minutes";
import { TasksTable } from "@/features/tasks";
import { formatDuration } from "@/lib/format";
import type { MeetingJob } from "@/lib/schemas";
import { isDone, isFailed, isProcessing } from "@/features/meeting/utils/meeting-status";

const paramsSchema = z.object({
  meetingId: z.string().regex(/^[0-9a-f]{12}$/),
});

export const Route = createFileRoute("/m/$meetingId")({
  ssr: false,
  params: {
    parse: (params) => paramsSchema.parse(params),
  },
  component: MeetingPage,
});

function MeetingPage() {
  const { meetingId } = Route.useParams();
  const { data: job, error, isPending } = useMeetingJob(meetingId);
  const reanalyze = useReanalyze(meetingId);

  if (isPending && !job) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <p className="text-sm text-[var(--color-ink-soft)]">{strings.processingTitle}</p>
      </main>
    );
  }
  if (error) {
    return <ErrorView message={isApiError(error) ? error.message_ar : ""} />;
  }
  if (!job) return null;

  if (isFailed(job.status)) {
    return <ErrorView message={job.error_ar ?? ""} />;
  }

  return (
    <PlayerProvider meetingId={job.id} sentences={job.sentences}>
      <MeetingBody
        job={job}
        onReanalyze={reanalyze.reanalyze}
        reanalyzePending={reanalyze.isPending}
      />
    </PlayerProvider>
  );
}

interface MeetingBodyProps {
  job: MeetingJob;
  onReanalyze: () => void;
  reanalyzePending: boolean;
}

function MeetingBody({ job, onReanalyze, reanalyzePending }: MeetingBodyProps) {
  const done = isDone(job.status);
  const processing = isProcessing(job.status);

  return (
    <main className="min-h-screen pb-40">
      <div className="mx-auto max-w-[880px] px-4 py-6">
        {done ? (
          <>
            <DoneHeader job={job} onReanalyze={onReanalyze} reanalyzePending={reanalyzePending} />
            <StatsStrip job={job} />
            <AnalysisBanner job={job} onReanalyze={onReanalyze} reanalyzePending={reanalyzePending} />
            <SpeakersBar
              meetingId={job.id}
              speakers={job.speakers}
              sentences={job.sentences}
              onSpeakersChanged={onReanalyze}
            />
            <PlayerConsumer job={job} />
          </>
        ) : null}
        {processing ? (
          <section className="space-y-6">
            <h1 className="text-xl font-semibold">{strings.processingTitle}</h1>
            <StagesList stages={job.stages} />
            {job.sentences.length > 0 ? (
              <SentenceList job={job} onSeek={noopSeek} />
            ) : null}
          </section>
        ) : null}
      </div>
    </main>
  );
}

function noopSeek(): void {}

interface PlayerConsumerProps {
  job: MeetingJob;
}

function PlayerConsumer({ job }: PlayerConsumerProps) {
  const { seekToSentence } = usePlayer();
  const startSeconds = job.sentences.reduce<Record<string, number>>((acc, s) => {
    acc[s.id] = s.start;
    return acc;
  }, {});
  return (
    <>
      <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_280px]">
        <section className="min-w-0">
          <h3 className="mb-3 text-lg font-semibold">{strings.transcriptHeading}</h3>
          <SentenceList job={job} onSeek={seekToSentence} />
        </section>
        <aside className="min-w-0 space-y-4">
          {job.analysis ? (
            <section>
              <h3 className="mb-2 text-lg font-semibold">{strings.topicsHeading}</h3>
              <MinutesSections
                topics={job.analysis.topics}
                decisions={job.analysis.decisions}
                directives={job.analysis.directives}
                startSeconds={startSeconds}
                onSeek={seekToSentence}
              />
            </section>
          ) : null}
          {job.analysis && job.analysis.tasks.length > 0 ? (
            <section>
              <div className="mb-2 flex items-baseline justify-between">
                <h3 className="m-0 text-lg font-semibold">{strings.followupTasks}</h3>
                <span className="text-xs tabular-nums text-[var(--color-ink-soft)]">
                  {job.duration_s != null ? formatDuration(job.duration_s) : ""}
                </span>
              </div>
              <TasksTable tasks={job.analysis.tasks} onSeek={seekToSentence} />
            </section>
          ) : null}
        </aside>
      </div>
      <SkimBar sentences={job.sentences} />
    </>
  );
}
