import { CircleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";

/** A failed load, said plainly with a way forward. Never a blank panel. */
export function ErrorPanel({
  error,
  onRetry,
  what = "this page",
}: {
  error: unknown;
  onRetry?: () => void;
  what?: string;
}) {
  const refused = error instanceof ApiError && error.status === 403;
  const notFound = error instanceof ApiError && error.status === 404;
  const message = refused
    ? "Your role does not include this."
    : notFound
      ? "That period or item does not exist."
      : "The server did not answer, or answered with an error.";
  return (
    <Alert variant="destructive">
      <CircleAlert aria-hidden />
      <AlertTitle className="text-base">We could not load {what}</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3">
        <p className="text-base">{message}</p>
        {onRetry && !refused && !notFound && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Try again
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
