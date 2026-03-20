import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const updateDatasetMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  isControllerApiError: vi.fn(),
  serializeControllerApiError: serializeControllerApiErrorMock,
  updateDataset: updateDatasetMock,
}));

describe("dataset patch route", () => {
  beforeEach(() => {
    updateDatasetMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  it("forwards dataset patch requests through the controller api helper", async () => {
    updateDatasetMock.mockResolvedValue({
      dataset: { id: "dataset_1" },
    });

    const { PATCH } = await import("./route");
    const request = new NextRequest("http://localhost/api/datasets/dataset_1", {
      method: "PATCH",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({ name: "Updated name" }),
    });

    const response = await PATCH(request, {
      params: Promise.resolve({ datasetId: "dataset_1" }),
    });

    expect(updateDatasetMock).toHaveBeenCalledWith(
      "dataset_1",
      { name: "Updated name" },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(200);
  });
});
