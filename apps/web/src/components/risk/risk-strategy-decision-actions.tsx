"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { RiskStrategy } from "@/lib/contracts";

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

type RiskStrategyDecisionActionsProps = {
  strategy: RiskStrategy;
};

export function RiskStrategyDecisionActions({ strategy }: RiskStrategyDecisionActionsProps) {
  const router = useRouter();
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (strategy.status !== "proposed") {
    return null;
  }

  async function refreshAfterMutation() {
    setErrorMessage(null);
    router.refresh();
  }

  async function handleDecision(decision: "approve" | "reject") {
    setPendingDecision(decision);
    setErrorMessage(null);

    try {
      await postJson(`/api/risk-strategies/${strategy.id}/${decision}`, {});
      await refreshAfterMutation();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Strategy decision failed.");
    } finally {
      setPendingDecision(null);
    }
  }

  return (
    <div className="stack-list">
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
      </div>
      {errorMessage ? (
        <p aria-live="polite" className="muted-text">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
