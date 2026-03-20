import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const headersMock = vi.fn();
const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  headers: headersMock,
  cookies: cookiesMock,
}));

describe("risk alert operation helpers", () => {
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

  it("patches risk alerts through the live backend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            risk_alert: {
              id: "alert_1",
              project_id: "proj_1",
              risk_signal_id: "signal_1",
              status: "investigating",
              severity: 70,
              title: "Updated alert",
              summary: "Updated summary",
              assigned_to_user_id: "user_pm_1",
              detected_by_workflow_run_id: "run_1",
              next_review_at: "2026-03-21T10:00:00Z",
              resolved_at: null,
            },
          },
          meta: {
            request_id: "req_patch",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { patchRiskAlert } = await import("./controller-api");
    const result = await patchRiskAlert(
      "alert_1",
      {
        status: "investigating",
        assigned_to_user_id: "user_pm_1",
        title: "Updated alert",
        summary: "Updated summary",
        severity: 70,
        next_review_at: "2026-03-21T10:00:00Z",
      },
      { idempotencyKey: "risk-alert-patch-1" },
    );

    expect(result.risk_alert?.id).toBe("alert_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/risk-alerts/alert_1",
      expect.objectContaining({
        method: "PATCH",
        cache: "no-store",
      }),
    );

    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Idempotency-Key")).toBe("risk-alert-patch-1");
  });

  it("acknowledges risk alerts through the live backend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            risk_alert: {
              id: "alert_1",
              project_id: "proj_1",
              risk_signal_id: "signal_1",
              status: "investigating",
              severity: 70,
              title: "Updated alert",
              summary: "Updated summary",
              assigned_to_user_id: "user_pm_1",
              detected_by_workflow_run_id: "run_1",
              next_review_at: null,
              resolved_at: null,
            },
          },
          meta: {
            request_id: "req_ack",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { acknowledgeRiskAlert } = await import("./controller-api");
    const result = await acknowledgeRiskAlert("alert_1");

    expect(result.risk_alert?.status).toBe("investigating");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/risk-alerts/alert_1/acknowledge",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Idempotency-Key")).toBe("risk-alert-acknowledge-alert_1-uuid-fixed");
  });
});
