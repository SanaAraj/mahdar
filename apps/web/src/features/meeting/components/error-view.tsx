import { useNavigate } from "@tanstack/react-router";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { strings } from "@/lib/strings";

interface ErrorViewProps {
  message: string;
}

export function ErrorView({ message }: Readonly<ErrorViewProps>) {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <div className="w-full max-w-[480px] rounded-[var(--radius-lg)] border border-[var(--color-line)] bg-[var(--color-surface)] p-8 text-center shadow-[var(--shadow-card)]">
        <h2 className="mb-4 text-xl font-bold">{strings.failedTitle}</h2>
        <Alert variant="danger" className="mb-6 text-right">
          <AlertTitle>{strings.failedTitle}</AlertTitle>
          <AlertDescription>{message || strings.pollFailedGeneric}</AlertDescription>
        </Alert>
        <div className="flex justify-center gap-2">
          <Button type="button" onClick={() => void navigate({ to: "/" })}>
            {strings.retry}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => void navigate({ to: "/" })}
          >
            {strings.newMeeting}
          </Button>
        </div>
      </div>
    </div>
  );
}
