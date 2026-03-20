import { beforeEach, describe, expect, it, vi } from "vitest";

const controllerApiMock = vi.hoisted(() => ({
  acknowledgeRiskAlert: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => ({
  acknowledgeRiskAlert: controllerApiMock.acknowledgeRiskAlert,
  isControllerApiError: vi.fn(),
  serializeControllerApiError: vi.fn(),
}));

describe("risk alert acknowledge route", () => {
  beforeEach(() => {
    controllerApiMock.acknowledgeRiskAlert.mockReset();
  });

  it("forwards acknowledge requests to the controller api helper", async () => {
    controllerApiMock.acknowledgeRiskAlert.mockResolvedValue({ risk_alert: { id: "alert_1" } });
    const { POST } = await import("./route");
    const request = new Request("http://test.local/api/risk-alerts/alert_1/acknowledge", {
      method: "POST",
    });

    const response = await POST(request as never, {
      params: Promise.resolve({ riskId: "alert_1" }),
    });

    expect(response.status).toBe(200);
    expect(controllerApiMock.acknowledgeRiskAlert).toHaveBeenCalledWith(
      "alert_1",
      expect.objectContaining({ requestHeaders: expect.any(Headers) }),
    );
  });

  it("generates an idempotency key when the browser request does not provide one", async () => {
    controllerApiMock.acknowledgeRiskAlert.mockResolvedValue({ risk_alert: { id: "alert_1" } });
    const { POST } = await import("./route");
    const request = new Request("http://test.local/api/risk-alerts/alert_1/acknowledge", {
      method: "POST",
    });

    await POST(request as never, {
      params: Promise.resolve({ riskId: "alert_1" }),
    });

    expect(controllerApiMock.acknowledgeRiskAlert).toHaveBeenCalledWith(
      "alert_1",
      expect.objectContaining({
        idempotencyKey: expect.stringMatching(/^risk-alert-acknowledge-alert_1-/),
      }),
    );
  });
});
