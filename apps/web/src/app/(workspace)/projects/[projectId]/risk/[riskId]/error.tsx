"use client";

import { useEffect } from "react";

import { PageHeader, SectionCard } from "@/components/ui/primitives";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk item detail"
        title="Risk alert failed to load"
        description="The controller response could not be rendered."
        actions={
          <div className="button-row">
            <button className="button-primary" type="button" onClick={reset}>
              Retry
            </button>
          </div>
        }
      />
      <SectionCard title="Error details">
        <p className="muted-text">{error.message}</p>
      </SectionCard>
    </div>
  );
}
