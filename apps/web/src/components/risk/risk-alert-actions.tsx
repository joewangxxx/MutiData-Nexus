"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import type { RiskAlertDetail } from "@/lib/controller-api";

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

async function requestJson(path: string, method: "PATCH" | "POST", body?: Record<string, unknown>) {
  const response = await fetch(path, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
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

type RiskAlertActionsProps = {
  alert: RiskAlertDetail;
};

export function RiskAlertActions({ alert }: RiskAlertActionsProps) {
  const router = useRouter();
  const [status, setStatus] = useState(alert.status);
  const [assignedToUserId, setAssignedToUserId] = useState(alert.assigned_to_user_id ?? "");
  const [title, setTitle] = useState(alert.title);
  const [summary, setSummary] = useState(alert.summary ?? "");
  const [severity, setSeverity] = useState(String(alert.severity));
  const [nextReviewAt, setNextReviewAt] = useState(toDateTimeLocalValue(alert.next_review_at));
  const [saving, setSaving] = useState(false);
  const [acknowledging, setAcknowledging] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      const parsedSeverity = Number(severity);
      await requestJson(`/api/risk-alerts/${alert.id}`, "PATCH", {
        ...compactObject({
          status,
          assigned_to_user_id: assignedToUserId.trim() ? assignedToUserId.trim() : null,
          title: title.trim() || undefined,
          summary: summary.trim() ? summary.trim() : null,
          severity: severity.trim() === "" || !Number.isFinite(parsedSeverity) ? undefined : parsedSeverity,
          next_review_at: toIsoOrNull(nextReviewAt),
        }),
      });

      setStatusMessage("Risk alert updated. Refreshing the dashboard.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Risk alert update failed.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAcknowledge() {
    setAcknowledging(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      await requestJson(`/api/risk-alerts/${alert.id}/acknowledge`, "POST");
      setStatusMessage("Risk alert acknowledged. Refreshing the dashboard.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Acknowledgement failed.");
    } finally {
      setAcknowledging(false);
    }
  }

  const acknowledgeDisabled = saving || acknowledging || status !== "open";

  return (
    <div className="stack-list">
      <form className="stack-list" onSubmit={handleSubmit}>
        <div className="section-grid">
          <label className="stack-list span-4">
            <span className="muted-text">Status</span>
            <select
              aria-label="Status"
              className="input-field"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {["open", "investigating", "mitigated", "resolved", "dismissed"].map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="stack-list span-4">
            <span className="muted-text">Assigned to user id</span>
            <input
              aria-label="Assigned to user id"
              className="input-field"
              value={assignedToUserId}
              onChange={(event) => setAssignedToUserId(event.target.value)}
              placeholder="user_..."
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
            />
          </label>
          <label className="stack-list span-6">
            <span className="muted-text">Next review at</span>
            <input
              aria-label="Next review at"
              className="input-field"
              type="datetime-local"
              value={nextReviewAt}
              onChange={(event) => setNextReviewAt(event.target.value)}
            />
          </label>
          <label className="stack-list span-12">
            <span className="muted-text">Summary</span>
            <textarea
              aria-label="Summary"
              className="input-field"
              rows={4}
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
            />
          </label>
        </div>
        <div className="button-row">
          <button className="button-primary" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save changes"}
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={handleAcknowledge}
            disabled={acknowledgeDisabled}
          >
            {acknowledging ? "Acknowledging..." : "Acknowledge alert"}
          </button>
        </div>
        {statusMessage ? (
          <p aria-live="polite" className="muted-text">
            {statusMessage}
          </p>
        ) : null}
        {status !== "open" ? (
          <p className="muted-text">Acknowledge is available when the alert is open.</p>
        ) : null}
        {errorMessage ? (
          <p aria-live="polite" className="muted-text">
            {errorMessage}
          </p>
        ) : null}
      </form>
    </div>
  );
}
