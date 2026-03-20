import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const headersMock = vi.fn();
const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  headers: headersMock,
  cookies: cookiesMock,
}));

describe("risk capture helpers", () => {
  beforeEach(() => {
    process.env.CONTROLLER_API_URL = "http://backend.test";
    headersMock.mockReturnValue(
      new Headers({
        authorization: "Bearer user-123",
        "x-request-id": "req-123",
      }),
    );
    cookiesMock.mockReturnValue({
      toString: () => "session=abc123",
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    delete process.env.CONTROLLER_API_URL;
  });

  it("creates risk signals through the live controller endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            risk_signal: {
              id: "signal_1",
              project_id: "proj_1",
              source_kind: "manual",
              signal_type: "delivery_delay",
              severity: 82,
              status: "open",
              title: "Vendor delivery is late",
              description: "Shipment missed the expected window.",
              signal_payload: { source: "manual" },
              observed_at: "2026-03-20T10:00:00Z",
              created_by_user_id: "user_pm_1",
            },
          },
          meta: {
            request_id: "req_signal",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { createProjectRiskSignal } = await import("./controller-api");
    const result = await createProjectRiskSignal(
      "proj_1",
      {
        source_kind: "manual",
        signal_type: "delivery_delay",
        severity: 82,
        title: "Vendor delivery is late",
        observed_at: "2026-03-20T10:00:00Z",
        description: "Shipment missed the expected window.",
        signal_payload: { source: "manual" },
      },
    );

    expect(result.risk_signal?.id).toBe("signal_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/risk-signals",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Idempotency-Key")).toBe("risk-signal-create-proj_1-uuid-fixed");
  });

  it("starts project risk generation through the live controller endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            ai_result: { id: "ai_1" },
            risk_strategies: [{ id: "strategy_1" }],
          },
          meta: {
            request_id: "req_generate",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 202, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { requestProjectRiskGeneration } = await import("./controller-api");
    const result = await requestProjectRiskGeneration(
      "proj_1",
      {
        source_kind: "workflow",
        signal_type: "quality_drop",
        severity: 75,
        title: "Quality drift detected",
        observed_at: "2026-03-20T11:30:00Z",
      },
    );

    expect(result.workflow_run?.id).toBe("run_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/risk-generate",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Idempotency-Key")).toBe("risk-generate-proj_1-uuid-fixed");
  });
});
