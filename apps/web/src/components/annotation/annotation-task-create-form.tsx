"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import type { SourceAsset } from "@/lib/contracts";

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

type AnnotationTaskCreateFormProps = {
  projectId: string;
  sourceAssets: SourceAsset[];
};

export function AnnotationTaskCreateForm({
  projectId,
  sourceAssets,
}: AnnotationTaskCreateFormProps) {
  const router = useRouter();
  const [sourceAssetId, setSourceAssetId] = useState(sourceAssets[0]?.id ?? "");
  const [taskType, setTaskType] = useState("annotation");
  const [priority, setPriority] = useState("50");
  const [assignedToUserId, setAssignedToUserId] = useState("");
  const [reviewerUserId, setReviewerUserId] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setStatusMessage(null);
    setErrorMessage(null);

    if (!sourceAssetId) {
      setErrorMessage("Select a source asset before creating a task.");
      setPending(false);
      return;
    }

    try {
      const parsedPriority = Number(priority);
      const payload = await postJson(`/api/projects/${projectId}/annotation-tasks`, {
        source_asset_id: sourceAssetId,
        task_type: taskType.trim(),
        ...compactObject({
          priority: priority.trim() === "" || !Number.isFinite(parsedPriority) ? undefined : parsedPriority,
          assigned_to_user_id: assignedToUserId.trim() || undefined,
          reviewer_user_id: reviewerUserId.trim() || undefined,
        }),
      });

      setStatusMessage(
        payload?.task?.id
          ? `Task ${payload.task.id} created. Refreshing the queue.`
          : "Task created. Refreshing the queue.",
      );
      setAssignedToUserId("");
      setReviewerUserId("");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Task creation failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="stack-list" onSubmit={handleSubmit}>
      <div className="section-grid">
        <label className="stack-list span-6">
          <span className="muted-text">Source asset</span>
          <select
            aria-label="Source asset"
            className="input-field"
            value={sourceAssetId}
            onChange={(event) => setSourceAssetId(event.target.value)}
            disabled={sourceAssets.length === 0}
          >
            {sourceAssets.length === 0 ? <option value="">No source assets available</option> : null}
            {sourceAssets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.asset_kind} {asset.id}
              </option>
            ))}
          </select>
        </label>
        <label className="stack-list span-6">
          <span className="muted-text">Task type</span>
          <input
            aria-label="Task type"
            className="input-field"
            value={taskType}
            onChange={(event) => setTaskType(event.target.value)}
            placeholder="image_labeling"
          />
        </label>
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
          <span className="muted-text">Assignee</span>
          <input
            aria-label="Assignee"
            className="input-field"
            value={assignedToUserId}
            onChange={(event) => setAssignedToUserId(event.target.value)}
            placeholder="user_..."
          />
        </label>
        <label className="stack-list span-4">
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
        <button className="button-primary" type="submit" disabled={pending || sourceAssets.length === 0}>
          {pending ? "Creating..." : "Create task"}
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
