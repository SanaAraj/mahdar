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
        variant="secondary"
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
      <Button asChild variant="secondary" size="sm">
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
      <div className="mb-6 text-center">
        <div className="mb-2 flex items-center justify-center gap-2">
          <Badge variant="success">{strings.ready}</Badge>
          <span className="text-sm text-[var(--color-ink-soft)]">
            {sentencesCount(job.sentences.length)}
          </span>
        </div>
        <h2 className="mb-1 text-2xl font-bold">{title}</h2>
        {meta ? <p className="text-sm text-[var(--color-ink-soft)]">{meta}</p> : null}
      </div>
    </>
  );
}
