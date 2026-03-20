import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("RiskStrategyDecisionActions", () => {
  beforeEach(() => {
    refreshMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("shows approve and reject actions only for proposed strategies and refreshes after approval", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            risk_strategies: [
              {
                id: "strategy_1",
              },
            ],
          },
          meta: {
            request_id: "req_1",
            next_cursor: null,
            has_more: false,
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { RiskStrategyDecisionActions } = await import("./risk-strategy-decision-actions");

    render(
      <RiskStrategyDecisionActions
        strategy={{
          id: "strategy_1",
          risk_alert_id: "alert_1",
          project_id: "proj_1",
          source_ai_result_id: null,
          status: "proposed",
          proposal_order: 1,
          title: "Strategy one",
          summary: "First proposal",
          strategy_payload: {},
          approved_by_user_id: null,
          approved_at: null,
          applied_at: null,
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/risk-strategies/strategy_1/approve",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("does not render decision buttons for approved strategies", async () => {
    const { RiskStrategyDecisionActions } = await import("./risk-strategy-decision-actions");

    render(
      <RiskStrategyDecisionActions
        strategy={{
          id: "strategy_2",
          risk_alert_id: "alert_1",
          project_id: "proj_1",
          source_ai_result_id: null,
          status: "approved",
          proposal_order: 2,
          title: "Strategy two",
          summary: "Already approved",
          strategy_payload: {},
          approved_by_user_id: "user_1",
          approved_at: "2026-03-19T10:00:00Z",
          applied_at: null,
        }}
      />,
    );

    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
  });

  it("surfaces route failures when rejecting a proposed strategy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "conflict",
            message: "Strategy is already closed.",
            details: [],
          },
        }),
        {
          status: 409,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { RiskStrategyDecisionActions } = await import("./risk-strategy-decision-actions");

    render(
      <RiskStrategyDecisionActions
        strategy={{
          id: "strategy_3",
          risk_alert_id: "alert_1",
          project_id: "proj_1",
          source_ai_result_id: null,
          status: "proposed",
          proposal_order: 3,
          title: "Strategy three",
          summary: "Needs attention",
          strategy_payload: {},
          approved_by_user_id: null,
          approved_at: null,
          applied_at: null,
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/risk-strategies/strategy_3/reject",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(screen.getByText("Strategy is already closed.")).toBeInTheDocument();
    expect(refreshMock).not.toHaveBeenCalled();
  });
});
