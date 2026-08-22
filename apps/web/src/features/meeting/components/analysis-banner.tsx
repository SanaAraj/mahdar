import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { MeetingJob } from "@/lib/schemas";
import { strings } from "@/lib/strings";

interface AnalysisBannerProps {
  job: MeetingJob;
  onReanalyze: () => void;
  reanalyzePending: boolean;
}

export function AnalysisBanner({
  job,
  onReanalyze,
  reanalyzePending,
}: Readonly<AnalysisBannerProps>) {
  const analyzeStage = job.stages.find((s) => s.key === "analyze");
  const running =
    reanalyzePending || job.status === "analyzing" || analyzeStage?.state === "running";
  const failed = analyzeStage?.state === "error";
  if (!running && !failed) return null;
  if (running) {
    return (
      <Alert variant="accent" className="mb-4">
        <AlertDescription>{strings.analyzeRunning}</AlertDescription>
      </Alert>
    );
  }
  return (
    <Alert variant="warn" className="mb-4 flex items-center justify-between gap-3">
      <AlertDescription>
        {analyzeStage?.note_ar || strings.analyzeFailedHint}
      </AlertDescription>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={onReanalyze}
        disabled={reanalyzePending}
      >
        {strings.reanalyze}
      </Button>
    </Alert>
  );
}
