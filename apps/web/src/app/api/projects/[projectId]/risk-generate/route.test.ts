import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const controllerApiMock = vi.hoisted(() => ({
  requestProjectRiskGeneration: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => ({
  isControllerApiError: vi.fn(),
  requestProjectRiskGeneration: controllerApiMock.requestProjectRiskGeneration,
  serializeControllerApiError: vi.fn(),
}));

describe("project risk generate route", () => {
  beforeEach(() => {
    controllerApiMock.requestProjectRiskGeneration.mockReset();
  });

  it("forwards risk generation requests through the controller api helper", async () => {
    controllerApiMock.requestProjectRiskGeneration.mockResolvedValue({
      workflow_run: { id: "run_1" },
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/risk-generate", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({
        source_kind: "workflow",
        signal_type: "quality_drop",
        severity: 75,
        title: "Quality drift detected",
        observed_at: "2026-03-20T11:30:00Z",
      }),
    });

    const response = await POST(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(controllerApiMock.requestProjectRiskGeneration).toHaveBeenCalledWith(
      "proj_1",
      {
        source_kind: "workflow",
        signal_type: "quality_drop",
        severity: 75,
        title: "Quality drift detected",
        observed_at: "2026-03-20T11:30:00Z",
      },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(202);
  });

  it("generates an idempotency key when the browser request does not provide one", async () => {
    controllerApiMock.requestProjectRiskGeneration.mockResolvedValue({
      workflow_run: { id: "run_1" },
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/risk-generate", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({
        source_kind: "workflow",
        signal_type: "quality_drop",
        severity: 75,
        title: "Quality drift detected",
        observed_at: "2026-03-20T11:30:00Z",
      }),
    });

    await POST(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(controllerApiMock.requestProjectRiskGeneration).toHaveBeenCalledWith(
      "proj_1",
      expect.any(Object),
      expect.objectContaining({
        idempotencyKey: expect.stringMatching(/^risk-generate-proj_1-/),
      }),
    );
  });
});
