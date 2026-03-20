import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const registerProjectSourceAssetMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  isControllerApiError: vi.fn(),
  registerProjectSourceAsset: registerProjectSourceAssetMock,
  serializeControllerApiError: serializeControllerApiErrorMock,
}));

describe("project source asset create route", () => {
  beforeEach(() => {
    registerProjectSourceAssetMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  it("forwards source asset registration requests through the controller api helper", async () => {
    registerProjectSourceAssetMock.mockResolvedValue({
      source_asset: { id: "asset_1" },
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/source-assets", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({
        asset_kind: "audio",
        uri: "https://example.com/media/1.wav",
      }),
    });

    const response = await POST(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(registerProjectSourceAssetMock).toHaveBeenCalledWith(
      "proj_1",
      {
        asset_kind: "audio",
        uri: "https://example.com/media/1.wav",
      },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(201);
  });
});
