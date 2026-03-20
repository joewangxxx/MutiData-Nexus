"use client";

import type { FormEvent } from "react";
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

type AnnotationTaskWorkbenchActionsProps = {
  taskId: string;
  initialLabels: string[];
  initialContent: string;
};

export function AnnotationTaskWorkbenchActions({
  taskId,
  initialLabels,
  initialContent,
}: AnnotationTaskWorkbenchActionsProps) {
  const router = useRouter();
  const [labels, setLabels] = useState(initialLabels.join(", "));
  const [content, setContent] = useState(initialContent);
  const [reviewNotes, setReviewNotes] = useState("");
  const [confidenceScore, setConfidenceScore] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<"generate" | "submit" | null>(null);

  function parseLabels(value: string) {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function refreshAfterMutation(message: string) {
    setStatusMessage(message);
    setErrorMessage(null);
    router.refresh();
  }

  async function handleGenerate() {
    setPendingAction("generate");
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await postJson(`/api/annotation-tasks/${taskId}/ai-generate`, {
        context_overrides: {
          labels: parseLabels(labels),
          content: { summary: content },
        },
        force_refresh: true,
      });
      await refreshAfterMutation("AI generation requested. Refreshing the workbench.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "AI generation failed.");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPendingAction("submit");
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await postJson(`/api/annotation-tasks/${taskId}/submissions`, {
        labels: parseLabels(labels),
        content: {
          summary: content,
        },
        ...compactObject({
          review_notes: reviewNotes.trim() || undefined,
          confidence_score:
            confidenceScore.trim() === "" || Number.isNaN(Number(confidenceScore))
              ? undefined
              : Number(confidenceScore),
        }),
      });
      await refreshAfterMutation("Revision submitted. Refreshing the workbench.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Submission failed.");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="stack-list">
      <button
        className="button-secondary"
        type="button"
        onClick={handleGenerate}
        disabled={pendingAction !== null}
      >
        {pendingAction === "generate" ? "Generating..." : "Generate AI suggestion"}
      </button>

      <form className="stack-list" onSubmit={handleSubmit}>
        <label className="stack-list">
          <span className="muted-text">Labels</span>
          <input
            aria-label="Labels"
            className="input-field"
            value={labels}
            onChange={(event) => setLabels(event.target.value)}
            placeholder="label_a, label_b"
          />
        </label>
        <label className="stack-list">
          <span className="muted-text">Content</span>
          <textarea
            aria-label="Content"
            className="textarea-field"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            rows={5}
          />
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
        <label className="stack-list">
          <span className="muted-text">Confidence score</span>
          <input
            aria-label="Confidence score"
            className="input-field"
            inputMode="decimal"
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={confidenceScore}
            onChange={(event) => setConfidenceScore(event.target.value)}
          />
        </label>
        <div className="button-row">
          <button
            className="button-primary"
            type="submit"
            disabled={pendingAction !== null}
          >
            {pendingAction === "submit" ? "Submitting..." : "Submit revision"}
          </button>
        </div>
      </form>

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
