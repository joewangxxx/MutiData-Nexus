"use client";

import type { AnnotationRevision } from "@/lib/contracts";
import { useState } from "react";
import { useRouter } from "next/navigation";

function compactObject<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== ""),
  ) as T;
}

async function postJson(path: string, body: Record<string, unknown>) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
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

type AnnotationTaskReviewControlsProps = {
  taskId: string;
  revisions: AnnotationRevision[];
};

function getLatestRevision(revisions: AnnotationRevision[]): AnnotationRevision | null {
  return revisions.reduce<AnnotationRevision | null>((latest, revision) => {
    if (!latest || revision.revision_no > latest.revision_no) {
      return revision;
    }
    return latest;
  }, null);
}

export function AnnotationTaskReviewControls({
  taskId,
  revisions,
}: AnnotationTaskReviewControlsProps) {
  const router = useRouter();
  const latestRevision = getLatestRevision(revisions);
  const [selectedRevisionId] = useState(latestRevision?.id ?? "");
  const [reviewNotes, setReviewNotes] = useState("");
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | "revise" | null>(
    null,
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function refreshAfterMutation(message: string) {
    setStatusMessage(message);
    setErrorMessage(null);
    router.refresh();
  }

  async function handleDecision(decision: "approve" | "reject" | "revise") {
    if (!selectedRevisionId) {
      setErrorMessage("Select a revision to review.");
      return;
    }

    setPendingDecision(decision);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await postJson(`/api/annotation-tasks/${taskId}/reviews`, {
        revision_id: selectedRevisionId,
        decision,
        ...compactObject({
          notes: reviewNotes.trim() || undefined,
        }),
      });

      await refreshAfterMutation(
        decision === "approve"
          ? "Revision approved. Refreshing the workbench."
          : decision === "reject"
            ? "Revision rejected. Refreshing the workbench."
            : "Revision marked for changes. Refreshing the workbench.",
      );
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Review submission failed.");
    } finally {
      setPendingDecision(null);
    }
  }

  return (
    <div className="stack-list">
      <label className="stack-list">
        <span className="muted-text">Revision</span>
        <select
          aria-label="Revision"
          className="input-field"
          value={selectedRevisionId}
          disabled
          onChange={() => undefined}
        >
          {latestRevision ? (
            <option value={latestRevision.id}>
              Revision {latestRevision.revision_no} Route {latestRevision.revision_kind}
            </option>
          ) : null}
        </select>
      </label>
      <label className="stack-list">
        <span className="muted-text">Review notes</span>
        <textarea
          aria-label="Review notes"
          className="textarea-field"
          value={reviewNotes}
          onChange={(event) => setReviewNotes(event.target.value)}
          rows={3}
        />
      </label>
      <div className="button-row">
        <button
          className="button-primary"
          type="button"
          onClick={() => handleDecision("approve")}
          disabled={pendingDecision !== null}
        >
          {pendingDecision === "approve" ? "Approving..." : "Approve"}
        </button>
        <button
          className="button-secondary"
          type="button"
          onClick={() => handleDecision("reject")}
          disabled={pendingDecision !== null}
        >
          {pendingDecision === "reject" ? "Rejecting..." : "Reject"}
        </button>
        <button
          className="button-secondary"
          type="button"
          onClick={() => handleDecision("revise")}
          disabled={pendingDecision !== null}
        >
          {pendingDecision === "revise" ? "Requesting..." : "Request revision"}
        </button>
      </div>
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
