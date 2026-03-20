"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

async function postJson(path: string) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({}),
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(
      payload?.error?.message ?? `Request to ${path} failed with status ${response.status}.`,
    );
  }

  return payload;
}

type AnnotationTaskQueueClaimButtonProps = {
  taskId: string;
  claimable: boolean;
};

export function AnnotationTaskQueueClaimButton({
  taskId,
  claimable,
}: AnnotationTaskQueueClaimButtonProps) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!claimable) {
    return <span className="muted-text">Not claimable</span>;
  }

  async function handleClaim() {
    setPending(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await postJson(`/api/annotation-tasks/${taskId}/claim`);
      setStatusMessage("Task claimed. Refreshing the queue.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Claim failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack-list">
      <button className="button-secondary" type="button" onClick={handleClaim} disabled={pending}>
        {pending ? "Claiming..." : "Claim task"}
      </button>
      {statusMessage ? (
        <p aria-live="polite" className="muted-text">
          {statusMessage}
        </p>
      ) : null}
      {errorMessage ? (
        <p aria-live="polite" className="muted-text">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
