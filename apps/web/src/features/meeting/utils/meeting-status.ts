import type { JobStatus } from "@/lib/schemas";

export const TERMINAL_STATUSES = ["done", "failed"] as const;
export type TerminalStatus = (typeof TERMINAL_STATUSES)[number];

export const STAGE_ORDER: readonly JobStatus[] = [
  "received",
  "converting",
  "transcribing",
  "diarizing",
  "assembling",
  "analyzing",
  "done",
];

export function isTerminal(status: JobStatus): status is TerminalStatus {
  return status === "done" || status === "failed";
}

export function isProcessing(status: JobStatus): boolean {
  return !isTerminal(status);
}

export function isDone(status: JobStatus): boolean {
  return status === "done";
}

export function isFailed(status: JobStatus): boolean {
  return status === "failed";
}

export function stageOrder(key: JobStatus): number {
  const idx = STAGE_ORDER.indexOf(key);
  return idx === -1 ? STAGE_ORDER.length : idx;
}
