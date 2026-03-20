import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const requestRiskStrategyDecisionMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  isControllerApiError: vi.fn(),
  requestRiskStrategyDecision: requestRiskStrategyDecisionMock,
  serializeControllerApiError: serializeControllerApiErrorMock,
}));

describe("risk strategy approve route", () => {
  beforeEach(() => {
    requestRiskStrategyDecisionMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("forwards approve requests through the controller api helper", async () => {
    requestRiskStrategyDecisionMock.mockResolvedValue({
      workflow_run: { id: "run_1" },
      coze_run: { id: "coze_1" },
      risk_strategies: [],
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/risk-strategies/strategy_1/approve", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
    });

    const response = await POST(request, { params: Promise.resolve({ strategyId: "strategy_1" }) });

    expect(requestRiskStrategyDecisionMock).toHaveBeenCalledWith(
      "strategy_1",
      "approve",
      {},
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(200);
  });
});
