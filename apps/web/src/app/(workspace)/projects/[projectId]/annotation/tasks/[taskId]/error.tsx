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
        title="Unable to load annotation workbench"
        description={error.message || "The live task request failed. Try again to reload the page."}
      />
      <button className="button-primary" type="button" onClick={reset}>
        Try again
      </button>
    </div>
  );
}

