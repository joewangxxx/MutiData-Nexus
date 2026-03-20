"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import type { AnnotationTask } from "@/lib/contracts";

function compactObject<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== ""),
  ) as T;
}

function toDateTimeLocalValue(value: string | null): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const offsetMinutes = date.getTimezoneOffset();
  return new Date(date.getTime() - offsetMinutes * 60_000).toISOString().slice(0, 16);
}

function toIsoOrUndefined(value: string): string | undefined {
  if (!value.trim()) {
    return undefined;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }

  return date.toISOString();
}

async function patchJson(path: string, body: Record<string, unknown>) {
  const response = await fetch(path, {
    method: "PATCH",
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

type AnnotationTaskManagementPanelProps = {
  task: AnnotationTask;
};

export function AnnotationTaskManagementPanel({ task }: AnnotationTaskManagementPanelProps) {
  const router = useRouter();
  const [priority, setPriority] = useState(String(task.priority));
  const [dueAt, setDueAt] = useState(toDateTimeLocalValue(task.due_at));
  const [assignedToUserId, setAssignedToUserId] = useState(task.assigned_to_user_id ?? "");
  const [reviewerUserId, setReviewerUserId] = useState(task.reviewer_user_id ?? "");
  const [status, setStatus] = useState(task.status);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      const parsedPriority = Number(priority);
      await patchJson(`/api/annotation-tasks/${task.id}`, {
        ...compactObject({
          priority: priority.trim() === "" || !Number.isFinite(parsedPriority) ? undefined : parsedPriority,
          due_at: toIsoOrUndefined(dueAt),
          assigned_to_user_id: assignedToUserId.trim() || undefined,
          reviewer_user_id: reviewerUserId.trim() || undefined,
          status,
        }),
      });

      setStatusMessage("Task updated. Refreshing the workbench.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Task update failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="stack-list" onSubmit={handleSubmit}>
      <div className="section-grid">
        <label className="stack-list span-4">
          <span className="muted-text">Priority</span>
          <input
            aria-label="Priority"
            className="input-field"
            inputMode="numeric"
            type="number"
            min="0"
            max="100"
            value={priority}
            onChange={(event) => setPriority(event.target.value)}
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Due at</span>
          <input
            aria-label="Due at"
            className="input-field"
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Status</span>
          <select
            aria-label="Status"
            className="input-field"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {[
              "queued",
              "claimed",
              "in_progress",
              "submitted",
              "needs_review",
              "approved",
              "rejected",
              "closed",
              "canceled",
            ].map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label className="stack-list span-6">
          <span className="muted-text">Assignee</span>
          <input
            aria-label="Assignee"
            className="input-field"
            value={assignedToUserId}
            onChange={(event) => setAssignedToUserId(event.target.value)}
            placeholder="user_..."
          />
        </label>
        <label className="stack-list span-6">
          <span className="muted-text">Reviewer</span>
          <input
            aria-label="Reviewer"
            className="input-field"
            value={reviewerUserId}
            onChange={(event) => setReviewerUserId(event.target.value)}
            placeholder="user_..."
          />
        </label>
      </div>
      <div className="button-row">
        <button className="button-primary" type="submit" disabled={pending}>
          {pending ? "Saving..." : "Save task changes"}
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
    </form>
  );
}
