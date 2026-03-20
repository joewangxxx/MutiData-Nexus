import { beforeEach, describe, expect, it, vi } from "vitest";

const controllerApiMock = vi.hoisted(() => ({
  patchRiskAlert: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => ({
  isControllerApiError: vi.fn(),
  patchRiskAlert: controllerApiMock.patchRiskAlert,
  serializeControllerApiError: vi.fn(),
}));

describe("risk alert patch route", () => {
  beforeEach(() => {
    controllerApiMock.patchRiskAlert.mockReset();
  });

  it("forwards patch requests to the controller api helper", async () => {
    controllerApiMock.patchRiskAlert.mockResolvedValue({ risk_alert: { id: "alert_1" } });
    const { PATCH } = await import("./route");
    const request = new Request("http://test.local/api/risk-alerts/alert_1", {
      method: "PATCH",
      body: JSON.stringify({ title: "Updated" }),
      headers: { "content-type": "application/json" },
    });

    const response = await PATCH(request as never, {
      params: Promise.resolve({ riskId: "alert_1" }),
    });

    expect(response.status).toBe(200);
    expect(controllerApiMock.patchRiskAlert).toHaveBeenCalledWith(
      "alert_1",
      { title: "Updated" },
      expect.objectContaining({ requestHeaders: expect.any(Headers) }),
    );
  });

  it("generates an idempotency key when the browser request does not provide one", async () => {
    controllerApiMock.patchRiskAlert.mockResolvedValue({ risk_alert: { id: "alert_1" } });
    const { PATCH } = await import("./route");
    const request = new Request("http://test.local/api/risk-alerts/alert_1", {
      method: "PATCH",
      body: JSON.stringify({ title: "Updated" }),
      headers: { "content-type": "application/json" },
    });

    await PATCH(request as never, {
      params: Promise.resolve({ riskId: "alert_1" }),
    });

    expect(controllerApiMock.patchRiskAlert).toHaveBeenCalledWith(
      "alert_1",
      { title: "Updated" },
      expect.objectContaining({
        idempotencyKey: expect.stringMatching(/^risk-alert-patch-alert_1-/),
      }),
    );
  });
});
