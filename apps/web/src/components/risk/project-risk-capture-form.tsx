"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

function compactObject<T extends Record<string, unknown>>(value: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== ""),
  ) as Partial<T>;
}

function toDateTimeLocalValue(value: Date): string {
  const offsetMinutes = value.getTimezoneOffset();
  return new Date(value.getTime() - offsetMinutes * 60_000).toISOString().slice(0, 16);
}

function toIsoOrNull(value: string): string | null {
  if (!value.trim()) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toISOString();
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
  let payload: { error?: { message?: string } } | null = null;

  if (text) {
    try {
      payload = JSON.parse(text) as { error?: { message?: string } };
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    throw new Error(
      payload?.error?.message ?? `Request to ${path} failed with status ${response.status}.`,
    );
  }

  return payload;
}

type ProjectRiskCaptureFormProps = {
  projectId: string;
};

type SubmitAction = "signal" | "analyze";

function buildStatusMessage(action: SubmitAction): string {
  return action === "signal"
    ? "Risk signal saved. Refreshing the dashboard."
    : "Risk signal saved and analysis started. Refreshing the dashboard.";
}

export function ProjectRiskCaptureForm({ projectId }: ProjectRiskCaptureFormProps) {
  const router = useRouter();
  const [sourceKind, setSourceKind] = useState("manual");
  const [signalType, setSignalType] = useState("");
  const [severity, setSeverity] = useState("50");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [observedAt, setObservedAt] = useState(toDateTimeLocalValue(new Date()));
  const [signalPayload, setSignalPayload] = useState("");
  const [pendingAction, setPendingAction] = useState<SubmitAction | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nativeEvent = event.nativeEvent as SubmitEvent & { submitter?: EventTarget | null };
    const submitter = nativeEvent.submitter as HTMLButtonElement | null;
    const action = submitter?.value === "analyze" ? "analyze" : "signal";

    setPendingAction(action);
    setStatusMessage(null);
    setErrorMessage(null);

    const parsedSeverity = Number(severity);
    const parsedObservedAt = toIsoOrNull(observedAt);
    if (!Number.isFinite(parsedSeverity)) {
      setErrorMessage("Severity must be a number.");
      setPendingAction(null);
      return;
    }
    if (!parsedObservedAt) {
      setErrorMessage("Observed at is required.");
      setPendingAction(null);
      return;
    }

    let parsedSignalPayload: Record<string, unknown> | undefined;
    if (signalPayload.trim()) {
      try {
        const value = JSON.parse(signalPayload) as unknown;
        if (!value || typeof value !== "object" || Array.isArray(value)) {
          throw new Error("Signal payload must be a JSON object.");
        }
        parsedSignalPayload = value as Record<string, unknown>;
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "Signal payload must be valid JSON.",
        );
        setPendingAction(null);
        return;
      }
    }

    const body = compactObject({
      source_kind: sourceKind.trim(),
      signal_type: signalType.trim(),
      severity: parsedSeverity,
      title: title.trim(),
      description: description.trim() || undefined,
      observed_at: parsedObservedAt,
      signal_payload: parsedSignalPayload,
    });

    if (!body.source_kind || !body.signal_type || !body.title) {
      setErrorMessage("Source kind, signal type, and title are required.");
      setPendingAction(null);
      return;
    }

    const path =
      action === "analyze"
        ? `/api/projects/${projectId}/risk-generate`
        : `/api/projects/${projectId}/risk-signals`;

    try {
      await postJson(path, body);
      setStatusMessage(buildStatusMessage(action));
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Risk capture failed.");
    } finally {
      setPendingAction(null);
    }
  }

  const pending = pendingAction !== null;

  return (
    <form className="stack-list" onSubmit={handleSubmit}>
      <div className="section-grid">
        <label className="stack-list span-4">
          <span className="muted-text">Source kind</span>
          <input
            aria-label="Source kind"
            className="input-field"
            value={sourceKind}
            onChange={(event) => setSourceKind(event.target.value)}
            placeholder="manual"
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Signal type</span>
          <input
            aria-label="Signal type"
            className="input-field"
            value={signalType}
            onChange={(event) => setSignalType(event.target.value)}
            placeholder="delivery_delay"
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Severity</span>
          <input
            aria-label="Severity"
            className="input-field"
            inputMode="numeric"
            type="number"
            min="0"
            max="100"
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
          />
        </label>
        <label className="stack-list span-6">
          <span className="muted-text">Title</span>
          <input
            aria-label="Title"
            className="input-field"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Vendor delivery is late"
          />
        </label>
        <label className="stack-list span-6">
          <span className="muted-text">Observed at</span>
          <input
            aria-label="Observed at"
            className="input-field"
            type="datetime-local"
            value={observedAt}
            onChange={(event) => setObservedAt(event.target.value)}
          />
        </label>
        <label className="stack-list span-12">
          <span className="muted-text">Description</span>
          <textarea
            aria-label="Description"
            className="input-field"
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Add context for the signal."
          />
        </label>
        <label className="stack-list span-12">
          <span className="muted-text">Signal payload</span>
          <textarea
            aria-label="Signal payload"
            className="input-field"
            rows={4}
            value={signalPayload}
            onChange={(event) => setSignalPayload(event.target.value)}
            placeholder='{"source":"manual"}'
          />
        </label>
      </div>
      <div className="button-row">
        <button className="button-secondary" type="submit" value="signal" disabled={pending}>
          {pendingAction === "signal" ? "Saving signal..." : "Save signal only"}
        </button>
        <button className="button-primary" type="submit" value="analyze" disabled={pending}>
          {pendingAction === "analyze" ? "Saving and analyzing..." : "Save and analyze"}
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
