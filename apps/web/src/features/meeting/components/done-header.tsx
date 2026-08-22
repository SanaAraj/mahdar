import type { ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";

import { getExportDocxUrl, getExportJsonUrl } from "@/lib/api-client";
import { metaLine } from "@/lib/format";
import type { MeetingJob } from "@/lib/schemas";
import { sentencesCount, strings } from "@/lib/strings";
import { AppHeader } from "@/components/app-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { iconHref } from "@/components/icon-sprite";

interface DoneHeaderProps {
  job: MeetingJob;
  onReanalyze: () => void;
  reanalyzePending: boolean;
}

export function DoneHeader({ job, onReanalyze, reanalyzePending }: Readonly<DoneHeaderProps>) {
  const navigate = useNavigate();
  const title = job.analysis?.title || strings.meetingFallback;
  const meta = metaLine(job);
  const actions: ReactNode = (
    <>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => void navigate({ to: "/" })}
      >
        {strings.newMeeting}
      </Button>
      <Button asChild variant="secondary" size="sm">
        <a href={getExportJsonUrl(job.id)} download>
          JSON
        </a>
      </Button>
      <Button asChild variant="primary" size="sm">
        <a href={getExportDocxUrl(job.id)} download>
          <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
            <use href={iconHref("download")} />
          </svg>
          {strings.exportDocx}
        </a>
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onReanalyze}
        disabled={reanalyzePending}
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
          <use href={iconHref("refresh")} />
        </svg>
        {reanalyzePending ? strings.analyzeRunning : strings.reanalyze}
      </Button>
    </>
  );
  return (
    <>
      <AppHeader
        onNewMeeting={() => void navigate({ to: "/" })}
        actions={actions}
      />
      <div className="mb-5 border-b border-[var(--color-line)] py-3 pb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Badge>{strings.ready}</Badge>
          <span className="text-sm text-[var(--color-ink-soft)]">{sentencesCount(job.sentences.length)}</span>
        </div>
        <h2 className="m-0 max-w-[850px] text-[clamp(28px,4vw,38px)] font-bold leading-[1.3] tracking-[-0.02em]">{title}</h2>
        {meta ? <p className="mt-2 mb-0 text-sm text-[var(--color-ink-soft)]">{meta}</p> : null}
      </div>
    </>
  );
}
