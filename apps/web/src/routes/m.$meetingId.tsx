import { useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import * as z from "zod";

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
import { isDone, isFailed } from "@/features/meeting/utils/meeting-status";
import { AppHeader } from "@/components/app-header";

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

  if (!isDone(job.status)) return <ProcessingMeeting job={job} />;

  return (
    <PlayerProvider meetingId={job.id} sentences={job.sentences}>
      <CompletedMeeting
        job={job}
        onReanalyze={reanalyze.reanalyze}
        reanalyzePending={reanalyze.isPending}
      />
    </PlayerProvider>
  );
}

function ProcessingMeeting({ job }: Readonly<{ job: MeetingJob }>) {
  const completed = job.stages.filter((stage) => stage.state === "done" || stage.state === "skipped").length;
  const progress = job.stages.length > 0 ? Math.round((completed / job.stages.length) * 100) : 0;
  return (
    <main className="min-h-screen pb-16">
      <div className="mx-auto max-w-[760px] px-4 py-5 sm:px-6">
        <AppHeader />
        <section className="mt-8 overflow-hidden rounded-[24px] border border-[var(--color-line)] bg-[var(--color-surface)] shadow-[var(--shadow-card)]">
          <div className="border-b border-[var(--color-line-soft)] px-6 py-7 text-center sm:px-10">
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
              <svg viewBox="0 0 20 20" aria-hidden="true" className="h-6 w-6 animate-spin">
                <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="30 20" />
              </svg>
            </span>
            <h1 className="m-0 text-2xl font-bold">{strings.processingTitle}</h1>
            <p className="mx-auto mt-2 mb-0 max-w-[480px] text-sm text-[var(--color-ink-soft)]">
              {strings.processingSubtitle}
            </p>
          </div>
          <div className="px-6 py-7 sm:px-10">
            <div className="mb-6">
              <div className="mb-2 flex items-center justify-between text-xs font-semibold text-[var(--color-ink-soft)]">
                <span>{strings.processingProgress}</span>
                <span className="tabular-nums text-[var(--color-accent)]">{progress}٪</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[var(--color-line-soft)]">
                <div className="h-full rounded-full bg-[var(--color-accent)] transition-[width] duration-500" style={{ width: `${progress}%` }} />
              </div>
            </div>
            <StagesList stages={job.stages} />
          </div>
        </section>
        {job.sentences.length > 0 ? (
          <section className="mt-6 rounded-[20px] border border-[var(--color-line)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow)]">
            <h2 className="mt-0 mb-3 text-base font-bold">{strings.transcriptHeading}</h2>
            <SentenceList job={job} onSeek={() => undefined} />
          </section>
        ) : null}
      </div>
    </main>
  );
}

interface CompletedMeetingProps {
  job: MeetingJob;
  onReanalyze: () => void;
  reanalyzePending: boolean;
}

function CompletedMeeting({ job, onReanalyze, reanalyzePending }: CompletedMeetingProps) {
  const player = usePlayer();
  const activeSentenceId = activeSentenceAt(job.sentences, player.currentTime)?.id;
  const startSeconds = useMemo(
    () =>
      job.sentences.reduce<Record<string, number>>((acc, sentence) => {
        acc[sentence.id] = sentence.start;
        return acc;
      }, {}),
    [job.sentences],
  );
  return (
    <main className="min-h-screen pb-16">
      <div className="mx-auto max-w-[1180px] px-4 py-3 sm:px-6 lg:px-8">
        <DoneHeader job={job} onReanalyze={onReanalyze} reanalyzePending={reanalyzePending} />
        <SkimBar sentences={job.sentences} />
        <StatsStrip job={job} />
        <AnalysisBanner job={job} onReanalyze={onReanalyze} reanalyzePending={reanalyzePending} />
        {job.speakers.length > 0 ? (
          <section className="mb-5 rounded-[12px] border border-[var(--color-line)] bg-[var(--color-surface)] px-5 py-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="m-0 text-base font-bold">{strings.speakerLabelsTitle}</h2>
              <span className="text-xs text-[var(--color-ink-soft)]">{strings.renameHint}</span>
            </div>
            <SpeakersBar
              meetingId={job.id}
              speakers={job.speakers}
              sentences={job.sentences}
              player={player}
              onSpeakersChanged={onReanalyze}
            />
          </section>
        ) : null}
        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
          <section className="min-w-0 rounded-[12px] border border-[var(--color-line)] bg-[var(--color-surface)] p-5 sm:p-6">
            <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-[var(--color-line-soft)] pb-3">
              <h2 className="m-0 text-xl font-bold">{strings.transcriptHeading}</h2>
              <span className="text-xs text-[var(--color-ink-soft)]">{job.sentences.length} جملة</span>
            </div>
            <SentenceList job={job} onSeek={player.seekToSentence} activeSentenceId={activeSentenceId} />
          </section>
          <aside className="min-w-0 space-y-5">
            {job.analysis ? (
              <section className="rounded-[12px] border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
                <h2 className="mt-0 mb-4 border-b border-[var(--color-line-soft)] pb-3 text-xl font-bold">{strings.topicsHeading}</h2>
                <MinutesSections
                  topics={job.analysis.topics}
                  decisions={job.analysis.decisions}
                  directives={job.analysis.directives}
                  startSeconds={startSeconds}
                  onSeek={player.seekToSentence}
                />
              </section>
            ) : null}
          </aside>
        </div>
        {job.analysis && job.analysis.tasks.length > 0 ? (
          <section className="mt-5 rounded-[12px] border border-[var(--color-line)] bg-[var(--color-surface)] p-5 sm:p-6">
            <div className="mb-4 flex items-baseline justify-between border-b border-[var(--color-line-soft)] pb-3">
              <h2 className="m-0 text-xl font-bold">{strings.followupTasks}</h2>
              <span className="text-xs tabular-nums text-[var(--color-ink-soft)]">
                {job.duration_s != null ? formatDuration(job.duration_s) : ""}
              </span>
            </div>
            <TasksTable tasks={job.analysis.tasks} onSeek={player.seekToSentence} />
          </section>
        ) : null}
      </div>
    </main>
  );
}

function activeSentenceAt(sentences: MeetingJob["sentences"], currentTime: number) {
  let low = 0;
  let high = sentences.length - 1;
  let active: MeetingJob["sentences"][number] | undefined;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    const sentence = sentences[middle];
    if (sentence.start <= currentTime) {
      active = sentence;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return active;
}
