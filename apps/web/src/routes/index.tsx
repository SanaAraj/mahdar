import { useState } from "react";
import { useEffect } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { JOB_ID_RE } from "@/lib/config";
import { strings } from "@/lib/strings";
import { useUpload } from "@/features/meeting/hooks/use-upload";
import { UploadProgress } from "@/features/meeting/components/upload-progress";
import {
  RecordIdle,
  RecordingPanel,
  blobToFile,
  useLevelMeter,
  useRecorder,
  useRecordTimer,
  type RecordIdleLabels,
  type RecordingPanelLabels,
} from "@/features/recording";
import { useBeforeUnload } from "@/features/meeting/hooks/use-before-unload";

const IDLE_LABELS: RecordIdleLabels = {
  subtitle: strings.appSubtitle,
  recordHint: strings.recordHint,
  recordAriaLabel: strings.startRecording,
  orDivider: strings.orDivider,
  uploadZoneLabel: strings.uploadZoneLabel,
  uploadFormats: strings.uploadFormats,
};

const RECORD_LABELS: RecordingPanelLabels = {
  title: strings.recordingTitle,
  stop: strings.stop,
  savingHint: strings.savingHint,
};

export const Route = createFileRoute("/")({
  ssr: false,
  component: HomePage,
});

function HomePage() {
  const navigate = useNavigate();
  const recorder = useRecorder();
  const [pageError, setPageError] = useState<string | null>(null);
  const upload = useUpload();

  useBeforeUnload(recorder.state === "recording" || recorder.state === "paused");

  useEffect(() => {
    const hash = window.location.hash;
    const id = hash.startsWith("#") ? hash.substring(1) : hash;
    if (JOB_ID_RE.test(id)) {
      void navigate({ to: "/m/$meetingId", params: { meetingId: id }, replace: true });
    }
  }, [navigate]);

  if (upload.isPending || upload.progressPct > 0) {
    return <UploadProgress progressPct={upload.progressPct} onCancel={upload.cancel} />;
  }

  return (
    <main className="min-h-screen py-3 sm:py-5">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        {pageError ? (
          <Alert variant="danger" className="mb-4">
            <AlertDescription>{pageError}</AlertDescription>
          </Alert>
        ) : null}
        <HomeBody
          recorder={recorder}
          onUpload={(file) => upload.upload(file)}
          onUploadError={setPageError}
        />
      </div>
    </main>
  );
}
interface HomeBodyProps {
  recorder: ReturnType<typeof useRecorder>;
  onUpload: (file: File) => void;
  onUploadError: (message: string | null) => void;
}

function HomeBody({ recorder, onUpload, onUploadError }: HomeBodyProps) {
  const levelMeter = useLevelMeter({ stream: recorder.stream });
  const timer = useRecordTimer({
    running: recorder.state === "recording" || recorder.state === "paused",
    paused: recorder.state === "paused",
  });

  if (recorder.state === "idle") {
    return (
      <RecordIdle
        labels={IDLE_LABELS}
        isSupported={recorder.isSupported}
        onStartRecording={startRecording}
        onFilePicked={(file) => onUpload(file)}
        onFileRejected={(reasonKey) => onUploadError(strings[reasonKey])}
      />
    );
  }

  async function startRecording(): Promise<void> {
    try {
      await recorder.start();
    } catch (err) {
      onUploadError(err instanceof Error ? err.message : strings.micDenied);
    }
  }

  async function handleStop(): Promise<void> {
    await recorder.stop().then((blob) => {
      if (!blob || blob.size === 0) {
        onUploadError(strings.noAudioCaptured);
        return;
      }
      const file = blobToFile(blob, strings.recordingBaseName);
      onUpload(file);
    });
  }

  return (
    <RecordingPanel
      labels={RECORD_LABELS}
      recorder={recorder}
      levelMeter={levelMeter}
      timer={timer}
      onStop={() => {
        void handleStop();
      }}
    />
  );
}
