import { useEffect, useRef, useState } from "react";

import { isApiError } from "@/lib/api-client";
import { CHIP_ERROR_MS } from "@/lib/config";
import type { Speaker } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

import type { RenameInput } from "../hooks/use-rename-speakers";
import { speakerColorFor } from "../utils/palette";
import { RenameForm } from "./rename-form";

export interface SpeakerChipProps {
  speaker: Speaker;
  segmentCount?: number;
  isPreviewing: boolean;
  isRenaming: boolean;
  renameErrorAr: string | null;
  onSelect: (speaker: Speaker) => void;
  onSample: (speaker: Speaker) => void;
  onRename: (input: RenameInput) => void;
  onRenameDismiss: () => void;
}

export function SpeakerChip({
  speaker,
  segmentCount,
  isPreviewing,
  isRenaming,
  renameErrorAr,
  onSelect,
  onSample,
  onRename,
  onRenameDismiss,
}: SpeakerChipProps) {
  const [editing, setEditing] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const errorTimerRef = useRef<number | null>(null);
  const color = speakerColorFor(speaker.id);

  useEffect(() => {
    if (renameErrorAr) {
      setLocalError(renameErrorAr);
      if (errorTimerRef.current !== null) window.clearTimeout(errorTimerRef.current);
      errorTimerRef.current = window.setTimeout(() => {
        setLocalError(null);
        errorTimerRef.current = null;
        onRenameDismiss();
      }, CHIP_ERROR_MS);
    }
    return () => {
      if (errorTimerRef.current !== null) {
        window.clearTimeout(errorTimerRef.current);
        errorTimerRef.current = null;
      }
    };
  }, [renameErrorAr, onRenameDismiss]);

  const beginEdit = (): void => {
    setEditing(true);
    onSelect(speaker);
  };

  const cancelEdit = (): void => {
    setEditing(false);
  };

  const submitEdit = ({ label }: { label: string }): void => {
    if (label.trim() === speaker.label) {
      setEditing(false);
      return;
    }
    onRename({ speakerId: speaker.id, label });
    setEditing(false);
  };

  const shownError = localError;

  return (
    <div
      className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-line)] p-1"
      style={{ background: color.bg }}
      data-speaker-id={speaker.id}
    >
      {editing ? (
        <RenameForm
          defaultLabel={speaker.label}
          ringColor={color.ring}
          submitting={isRenaming}
          onSubmit={submitEdit}
          onCancel={cancelEdit}
        />
      ) : (
        <button
          type="button"
          onClick={beginEdit}
          aria-label={`${strings.renameLabel}: ${speaker.label}`}
          className="rounded-full px-2.5 py-1 text-[13px] font-semibold transition hover:underline focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{ color: color.ink, outlineColor: color.ring }}
        >
          {speaker.label}
          {typeof segmentCount === "number" ? (
            <span className="ms-1 text-[11px] opacity-70">({segmentCount})</span>
          ) : null}
        </button>
      )}
      {!editing && (
        <button
          type="button"
          onClick={() => onSample(speaker)}
          title={strings.playSample}
          aria-label={`${strings.playSample}: ${speaker.label}`}
          aria-pressed={isPreviewing}
          className={cn(
            "flex h-6 w-6 items-center justify-center rounded-full text-white transition focus-visible:outline-2 focus-visible:outline-offset-2",
            isPreviewing ? "opacity-60" : "opacity-100",
          )}
          style={{ background: color.ring, outlineColor: color.ring }}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true" width="12" height="12">
            <path d="M4 2.5v11l9-5.5z" fill="currentColor" />
          </svg>
        </button>
      )}
      {shownError ? (
        <span
          role="alert"
          className="px-1.5 text-[12px] text-[var(--color-danger)]"
        >
          {shownError}
        </span>
      ) : null}
    </div>
  );
}

export function extractRenameErrorAr(err: unknown): string {
  if (isApiError(err) && err.message_ar) return err.message_ar;
  return strings.renameFailed;
}
