import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { ALLOWED_EXTENSIONS, BYTES_PER_UPLOAD_MB } from "@/lib/config";
import { AppHeader } from "@/components/app-header";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

export interface RecordIdleLabels {
  subtitle: string;
  recordHint: string;
  recordAriaLabel: string;
  orDivider: string;
  uploadZoneLabel: string;
  uploadFormats: string;
}

export interface RecordIdleProps {
  labels: RecordIdleLabels;
  isSupported: boolean;
  onStartRecording: () => void;
  onFilePicked: (file: File) => void;
  onFileRejected: (reasonKey: "invalidFile" | "fileTooLarge") => void;
}

const ACCEPT_ATTR = buildAcceptAttr();

function buildAcceptAttr(): string {
  const exts = ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",");
  return `audio/*,${exts}`;
}

function fileExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  if (idx < 0) return "";
  return name.slice(idx + 1).toLowerCase();
}

export function RecordIdle({
  labels,
  isSupported,
  onStartRecording,
  onFilePicked,
  onFileRejected,
}: RecordIdleProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const acceptFile = (candidate: File | null | undefined) => {
    if (!candidate) return;
    const ext = fileExtension(candidate.name);
    const okType =
      candidate.type.startsWith("audio/") ||
      candidate.type === "video/mp4" ||
      (ALLOWED_EXTENSIONS as readonly string[]).includes(ext);
    if (!okType) {
      onFileRejected("invalidFile");
      return;
    }
    if (candidate.size > BYTES_PER_UPLOAD_MB) {
      onFileRejected("fileTooLarge");
      return;
    }
    onFilePicked(candidate);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    acceptFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const handleDragOver = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  return (
    <section aria-labelledby="rec-idle-title">
      <AppHeader className="mb-8" />
      <div className="grid min-h-[calc(100vh-160px)] items-center gap-10 pb-10 lg:grid-cols-[minmax(0,1fr)_500px] lg:gap-16">
        <div className="max-w-[600px] py-4">
          <p className="mb-4 text-sm font-semibold text-[var(--color-accent)]">محاضر اجتماعات عربية، في مكان واحد</p>
          <h1 id="rec-idle-title" className="m-0 max-w-[560px] text-[clamp(38px,5vw,64px)] font-bold leading-[1.18] tracking-[-0.035em]">
            حوّل اجتماعاتك إلى محاضر واضحة
          </h1>
          <p className="mt-5 mb-0 max-w-[570px] text-lg leading-[1.9] text-[var(--color-ink-soft)] sm:text-xl">
            {labels.subtitle}
          </p>
          <dl className="mt-10 grid max-w-[570px] grid-cols-1 border-y border-[var(--color-line)] sm:grid-cols-3 sm:divide-x sm:divide-x-reverse sm:divide-[var(--color-line)]">
            <div className="py-4 sm:px-4 sm:first:pr-0">
              <dt className="text-sm font-bold">تفريغ زمني</dt>
              <dd className="m-0 mt-1 text-xs text-[var(--color-ink-soft)]">انتقل مباشرة إلى أي جملة</dd>
            </div>
            <div className="border-t border-[var(--color-line)] py-4 sm:border-t-0 sm:px-4">
              <dt className="text-sm font-bold">فصل المتحدثين</dt>
              <dd className="m-0 mt-1 text-xs text-[var(--color-ink-soft)]">نص منظم حسب المتحدث</dd>
            </div>
            <div className="border-t border-[var(--color-line)] py-4 sm:border-t-0 sm:px-4 sm:last:pl-0">
              <dt className="text-sm font-bold">محضر قابل للتصدير</dt>
              <dd className="m-0 mt-1 text-xs text-[var(--color-ink-soft)]">قرارات ومهام بصيغة DOCX</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-[16px] border border-[var(--color-line)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-card)] sm:p-7">
          <div className="mb-6">
            <h2 className="m-0 text-xl font-bold">ابدأ اجتماعًا جديدًا</h2>
            <p className="mt-1 mb-0 text-sm text-[var(--color-ink-soft)]">سجّل مباشرة أو ارفع ملفًا موجودًا.</p>
          </div>
          <button
            type="button"
            onClick={onStartRecording}
            disabled={!isSupported}
            aria-label={labels.recordAriaLabel}
            className={cn(
              "flex min-h-14 w-full items-center justify-center gap-3 rounded-[10px] border border-[var(--color-accent)] bg-[var(--color-accent)] px-5 py-3 text-base font-bold text-white transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]",
              isSupported
                ? "cursor-pointer hover:bg-[var(--color-accent-dark)]"
                : "cursor-not-allowed opacity-50",
            )}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5">
              <use href="#icon-mic" />
            </svg>
            <span>{labels.recordAriaLabel}</span>
          </button>
          <p className="mt-2 mb-0 text-center text-xs text-[var(--color-ink-soft)]">{labels.recordHint}</p>
          <div className="my-5 flex items-center gap-3 text-xs text-[var(--color-ink-soft)]">
            <span className="h-px flex-1 bg-[var(--color-line)]" />
            <span>{labels.orDivider}</span>
            <span className="h-px flex-1 bg-[var(--color-line)]" />
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            hidden
            onChange={handleInputChange}
            aria-hidden="true"
            tabIndex={-1}
          />
          <label
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={cn(
              "flex min-h-[138px] w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-[10px] border border-dashed border-[var(--color-line)] bg-[var(--color-bg)] px-5 py-6 text-center transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]",
              dragOver
                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                : "hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)]",
            )}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" className="mb-1 h-5 w-5 text-[var(--color-accent)]">
              <use href="#icon-upload" />
            </svg>
            <span className="text-base font-bold text-[var(--color-ink)]">{labels.uploadZoneLabel}</span>
            <span dir="auto" className="text-xs text-[var(--color-ink-soft)]">{labels.uploadFormats}</span>
          </label>
          {!isSupported ? (
            <p role="alert" className="mt-5 mb-0 text-sm text-[var(--color-danger)]">{strings.micUnsupported}</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
