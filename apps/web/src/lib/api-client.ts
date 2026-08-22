import {
  meetingJobSchema,
  speakerSchema,
  type MeetingJob,
  type Speaker,
} from "./schemas";
import * as z from "zod";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly message_ar: string;

  constructor(status: number, code: string, messageAr: string) {
    super(messageAr || code);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.message_ar = messageAr;
  }
}

function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

export { isApiError };

async function parseErrorBody(resp: Response): Promise<{ code: string; message_ar: string }> {
  const fallback = { code: "http.error", message_ar: resp.statusText };
  let body: unknown;
  try {
    body = await resp.json();
  } catch {
    return fallback;
  }
  if (typeof body !== "object" || body === null) return fallback;
  const rec = body as Record<string, unknown>;
  const message_ar =
    typeof rec.error_ar === "string"
      ? rec.error_ar
      : typeof rec.detail === "string"
        ? rec.detail
        : resp.statusText;
  const code = typeof rec.code === "string" ? rec.code : "http.error";
  return { code, message_ar };
}

async function requestJson<T>(resp: Response, schema: z.ZodType<T>): Promise<T> {
  if (!resp.ok) {
    const { code, message_ar } = await parseErrorBody(resp);
    throw new ApiError(resp.status, code, message_ar);
  }
  const data: unknown = await resp.json();
  return schema.parse(data);
}

export async function getMeeting(id: string): Promise<MeetingJob> {
  const resp = await fetch(`/api/meetings/${id}`);
  return requestJson(resp, meetingJobSchema);
}

export function getAudioUrl(id: string): string {
  return `/api/meetings/${id}/audio`;
}

export function getExportJsonUrl(id: string): string {
  return `/api/meetings/${id}/export/json`;
}

export function getExportDocxUrl(id: string): string {
  return `/api/meetings/${id}/export/docx`;
}

export interface UploadOptions {
  onProgress?: (percent: number) => void;
  signal?: AbortSignal;
}

export function uploadMeetingFile(
  blob: Blob,
  filename: string,
  options: UploadOptions = {},
): Promise<MeetingJob> {
  const { onProgress, signal } = options;
  return new Promise<MeetingJob>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/meetings");

    const form = new FormData();
    form.append("audio", blob, filename);

    function onAbort(): void {
      xhr.abort();
    }

    if (signal) {
      if (signal.aborted) {
        reject(new ApiError(0, "upload.aborted", ""));
        return;
      }
      signal.addEventListener("abort", onAbort, { once: true });
    }

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      cleanup();
      if (xhr.status === 201) {
        try {
          const body = JSON.parse(xhr.responseText) as Record<string, unknown>;
          const id = typeof body.id === "string" ? body.id : "";
          if (id) {
            getMeeting(id).then(resolve, reject);
            return;
          }
        } catch {
          reject(new ApiError(xhr.status, "parse.error", ""));
          return;
        }
        reject(new ApiError(xhr.status, "parse.error", ""));
        return;
      }
      let message_ar = xhr.statusText;
      let code = "http.error";
      try {
        const body = JSON.parse(xhr.responseText) as Record<string, unknown>;
        if (typeof body.error_ar === "string") message_ar = body.error_ar;
        else if (typeof body.detail === "string") message_ar = body.detail;
        if (typeof body.code === "string") code = body.code;
      } catch {
        message_ar = xhr.statusText;
      }
      reject(new ApiError(xhr.status, code, message_ar));
    });

    xhr.addEventListener("error", () => {
      cleanup();
      reject(new ApiError(0, "network.error", ""));
    });

    xhr.addEventListener("abort", () => {
      cleanup();
      reject(new ApiError(0, "upload.aborted", ""));
    });

    function cleanup(): void {
      if (signal) signal.removeEventListener("abort", onAbort);
    }

    xhr.send(form);
  });
}

const speakersResponseSchema = z.array(speakerSchema);

export async function renameSpeakers(
  id: string,
  mapping: Record<string, string>,
): Promise<Speaker[]> {
  const resp = await fetch(`/api/meetings/${id}/speakers`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speakers: mapping }),
  });
  return requestJson(resp, speakersResponseSchema);
}

const idResponseSchema = z.object({ id: z.string() });

export async function reanalyze(id: string): Promise<{ id: string }> {
  const resp = await fetch(`/api/meetings/${id}/analyze`, { method: "POST" });
  return requestJson(resp, idResponseSchema);
}
