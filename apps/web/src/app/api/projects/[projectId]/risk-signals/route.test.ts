import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const controllerApiMock = vi.hoisted(() => ({
  createProjectRiskSignal: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => ({
  createProjectRiskSignal: controllerApiMock.createProjectRiskSignal,
  isControllerApiError: vi.fn(),
  serializeControllerApiError: vi.fn(),
}));

describe("project risk signal create route", () => {
  beforeEach(() => {
    controllerApiMock.createProjectRiskSignal.mockReset();
  });

  it("forwards risk signal creation requests through the controller api helper", async () => {
    controllerApiMock.createProjectRiskSignal.mockResolvedValue({
      risk_signal: { id: "signal_1" },
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/risk-signals", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({
        source_kind: "manual",
        signal_type: "delivery_delay",
        severity: 80,
        title: "Vendor delivery is late",
        observed_at: "2026-03-20T10:00:00Z",
      }),
    });

    const response = await POST(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(controllerApiMock.createProjectRiskSignal).toHaveBeenCalledWith(
      "proj_1",
      {
        source_kind: "manual",
        signal_type: "delivery_delay",
        severity: 80,
        title: "Vendor delivery is late",
        observed_at: "2026-03-20T10:00:00Z",
      },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(202);
  });

  it("generates an idempotency key when the browser request does not provide one", async () => {
    controllerApiMock.createProjectRiskSignal.mockResolvedValue({
      risk_signal: { id: "signal_1" },
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/risk-signals", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({
        source_kind: "manual",
        signal_type: "delivery_delay",
        severity: 80,
        title: "Vendor delivery is late",
        observed_at: "2026-03-20T10:00:00Z",
      }),
    });

    await POST(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(controllerApiMock.createProjectRiskSignal).toHaveBeenCalledWith(
      "proj_1",
      expect.any(Object),
      expect.objectContaining({
        idempotencyKey: expect.stringMatching(/^risk-signal-create-proj_1-/),
      }),
    );
  });
});
