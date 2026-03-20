import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const updateSourceAssetMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  isControllerApiError: vi.fn(),
  serializeControllerApiError: serializeControllerApiErrorMock,
  updateSourceAsset: updateSourceAssetMock,
}));

describe("source asset patch route", () => {
  beforeEach(() => {
    updateSourceAssetMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  it("forwards source asset patch requests through the controller api helper", async () => {
    updateSourceAssetMock.mockResolvedValue({
      source_asset: { id: "asset_1" },
    });

    const { PATCH } = await import("./route");
    const request = new NextRequest("http://localhost/api/source-assets/asset_1", {
      method: "PATCH",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({ transcript: "Updated" }),
    });

    const response = await PATCH(request, {
      params: Promise.resolve({ assetId: "asset_1" }),
    });

    expect(updateSourceAssetMock).toHaveBeenCalledWith(
      "asset_1",
      { transcript: "Updated" },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(200);
  });
});
