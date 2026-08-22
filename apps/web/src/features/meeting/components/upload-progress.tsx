import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { strings } from "@/lib/strings";

interface UploadProgressProps {
  progressPct: number;
  onCancel: () => void;
}

export function UploadProgress({ progressPct, onCancel }: Readonly<UploadProgressProps>) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6">
      <div className="w-full max-w-[480px] rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-surface)] p-8 text-center shadow-[var(--shadow-card)]">
        <h2 className="mb-4 text-xl font-bold">{strings.uploadingTitle}</h2>
        <p className="mb-2 text-4xl font-bold tabular-nums text-[var(--color-accent)]">
          {progressPct}٪
        </p>
        <div className="mb-4 flex justify-center">
          <Progress value={progressPct} />
        </div>
        <p className="mb-6 text-sm text-[var(--color-ink-soft)]">{strings.uploadWait}</p>
        <Button type="button" variant="secondary" onClick={onCancel}>
          {strings.cancel}
        </Button>
      </div>
    </div>
  );
}
