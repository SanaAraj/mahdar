import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { strings } from "@/lib/strings";

interface UploadProgressProps {
  progressPct: number;
  onCancel: () => void;
}

export function UploadProgress({ progressPct, onCancel }: Readonly<UploadProgressProps>) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-5">
      <div className="w-full max-w-[560px] overflow-hidden rounded-[26px] border border-[var(--color-line)] bg-[var(--color-surface)] shadow-[var(--shadow-card)]">
        <div className="border-b border-[var(--color-line-soft)] px-7 py-6 text-center sm:px-10">
          <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-[16px] bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6"><use href="#icon-upload" /></svg>
          </span>
          <h2 className="m-0 text-2xl font-bold">{strings.uploadingTitle}</h2>
          <p className="mt-2 mb-0 text-sm text-[var(--color-ink-soft)]">نرفع التسجيل بأمان ثم نبدأ المعالجة تلقائيًا</p>
        </div>
        <div className="px-7 py-8 text-center sm:px-10">
          <p className="mb-4 text-5xl font-bold tabular-nums text-[var(--color-accent)]">
          {progressPct}٪
          </p>
          <div className="mb-4 flex justify-center"><Progress value={progressPct} /></div>
          <p className="mb-6 text-sm text-[var(--color-ink-soft)]">{strings.uploadWait}</p>
          <Button type="button" variant="secondary" onClick={onCancel}>{strings.cancel}</Button>
        </div>
      </div>
    </div>
  );
}
