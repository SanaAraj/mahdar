import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";

import { uploadMeetingFile, type ApiError } from "@/lib/api-client";
import type { MeetingJob } from "@/lib/schemas";

interface UploadVariables {
  file: File;
}

interface UseUploadResult {
  progressPct: number;
  isPending: boolean;
  error: ApiError | null;
  upload: (file: File) => void;
  cancel: () => void;
  reset: () => void;
}

export function useUpload(): UseUploadResult {
  const navigate = useNavigate();
  const [progressPct, setProgressPct] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const mutation = useMutation<MeetingJob, ApiError, UploadVariables>({
    mutationFn: ({ file }) => {
      const controller = new AbortController();
      abortRef.current = controller;
      return uploadMeetingFile(file, file.name, {
        signal: controller.signal,
        onProgress: setProgressPct,
      });
    },
    onSuccess: (job) => {
      abortRef.current = null;
      void navigate({
        to: "/m/$meetingId",
        params: { meetingId: job.id },
        replace: true,
      });
    },
    onError: () => {
      setProgressPct(0);
    },
    onSettled: () => {
      abortRef.current = null;
    },
  });

  function upload(file: File): void {
    setProgressPct(0);
    mutation.mutate({ file });
  }

  function cancel(): void {
    abortRef.current?.abort();
    abortRef.current = null;
    mutation.reset();
    setProgressPct(0);
  }

  function reset(): void {
    mutation.reset();
    setProgressPct(0);
  }

  return {
    progressPct,
    isPending: mutation.isPending,
    error: mutation.error ?? null,
    upload,
    cancel,
    reset,
  };
}
