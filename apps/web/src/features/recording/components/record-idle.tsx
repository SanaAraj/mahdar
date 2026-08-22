import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { ALLOWED_EXTENSIONS, BYTES_PER_UPLOAD_MB } from "@/lib/config";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

export interface RecordIdleLabels {
  title: string;
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
    <section aria-labelledby="rec-idle-title" className="text-center">
      <div className="mx-auto my-12 max-w-[var(--width-card)] rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-surface)] px-6 py-10 shadow-[var(--shadow-card)] sm:px-10 sm:py-12">
        <h2
          id="rec-idle-title"
          className="m-0 mb-2 text-[clamp(26px,4vw,32px)] font-bold leading-[1.3]"
        >
          {labels.title}
        </h2>
        <p className="m-0 text-[17px] text-[var(--color-ink-soft)]">{labels.subtitle}</p>
        <div className="pt-8 pb-2">
          <button
            type="button"
            onClick={onStartRecording}
            disabled={!isSupported}
            aria-label={labels.recordAriaLabel}
            className={cn(
              "mx-auto flex h-[var(--record-size)] w-[var(--record-size)] items-center justify-center rounded-full border-none bg-[var(--color-accent)] text-white shadow-[0_0_0_var(--record-halo)_var(--color-accent-ring)] transition-[transform,box-shadow,background] duration-150",
              isSupported
                ? "cursor-pointer hover:scale-[1.03] hover:bg-[var(--color-accent-dark)] hover:shadow-[0_0_0_calc(var(--record-halo)+4px)_var(--color-accent-ring)] active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                : "cursor-not-allowed opacity-50",
            )}
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
              className="h-[calc(var(--record-size)*0.34)] w-[calc(var(--record-size)*0.34)]"
            >
              <circle cx="12" cy="12" r="7" fill="currentColor" />
            </svg>
          </button>
          <p className="mt-6 mb-0 text-[15px] font-medium text-[var(--color-ink-soft)]">
            {labels.recordHint}
          </p>
        </div>
        <div className="my-8 flex items-center gap-6 text-[14px] text-[var(--color-ink-soft)]">
          <span aria-hidden="true" className="flex-1 border-t border-[var(--color-line-soft)]" />
          <span className="rounded-full bg-[var(--color-bg)] px-[10px] py-[2px]">
            {labels.orDivider}
          </span>
          <span aria-hidden="true" className="flex-1 border-t border-[var(--color-line-soft)]" />
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
            "flex w-full cursor-pointer items-center justify-center gap-4 rounded-[var(--radius-lg)] border-[1.5px] border-dashed border-[var(--color-line)] bg-[var(--color-accent-ring)] px-4 py-6 transition-[border-color,background,box-shadow] duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]",
            dragOver && "border-[var(--color-accent)] bg-[var(--color-accent-soft)]",
          )}
        >
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            className="h-[14px] w-[14px] text-[var(--color-accent)]"
          >
            <use href="#icon-upload" />
          </svg>
          <span className="text-base font-semibold text-[var(--color-ink)]">
            {labels.uploadZoneLabel}
          </span>
        </label>
        <p dir="auto" className="mt-4 mb-0 text-sm text-[var(--color-ink-soft)]">
          {labels.uploadFormats}
        </p>
        {!isSupported ? (
          <p role="alert" className="mt-4 mb-0 text-sm text-[var(--color-danger)]">
            {strings.micUnsupported}
          </p>
        ) : null}
      </div>
    </section>
  );
}
