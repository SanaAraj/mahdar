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
    <div className="flex min-h-screen flex-col items-center justify-center p-5">
      <div className="w-full max-w-[540px] overflow-hidden rounded-[26px] border border-[var(--color-line)] bg-[var(--color-surface)] shadow-[var(--shadow-card)]">
        <div className="px-7 pt-8 text-center sm:px-10">
          <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-danger-soft)] text-[var(--color-danger)]">
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-7 w-7"><use href="#icon-alert-circle" /></svg>
          </span>
          <h2 className="m-0 text-2xl font-bold">{strings.failedTitle}</h2>
        </div>
        <div className="px-7 py-7 sm:px-10">
          <Alert variant="danger" className="mb-6 text-right">
          <AlertTitle>سبب المشكلة</AlertTitle>
          <AlertDescription>{message || strings.pollFailedGeneric}</AlertDescription>
          </Alert>
          <Button type="button" className="w-full" onClick={() => void navigate({ to: "/" })}>{strings.newMeeting}</Button>
        </div>
      </div>
    </div>
  );
}
