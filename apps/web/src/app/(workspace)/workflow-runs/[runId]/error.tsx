"use client";

import { EmptyState } from "@/components/ui/primitives";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="page-stack">
      <EmptyState
        title="Unable to load workflow detail"
        description={error.message || "The live workflow request failed. Try again to reload the page."}
      />
      <button className="button-primary" type="button" onClick={reset}>
        Try again
      </button>
    </div>
  );
}

