import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const createProjectDatasetMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  createProjectDataset: createProjectDatasetMock,
  isControllerApiError: vi.fn(),
  serializeControllerApiError: serializeControllerApiErrorMock,
}));

describe("project dataset create route", () => {
  beforeEach(() => {
    createProjectDatasetMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  it("forwards dataset creation requests through the controller api helper", async () => {
    createProjectDatasetMock.mockResolvedValue({
      dataset: { id: "dataset_1" },
    });

    const { POST } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/datasets", {
      method: "POST",
      headers: {
        authorization: "Bearer token",
      },
      body: JSON.stringify({
        name: "Incoming media",
        source_kind: "manual",
      }),
    });

    const response = await POST(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(createProjectDatasetMock).toHaveBeenCalledWith(
      "proj_1",
      {
        name: "Incoming media",
        source_kind: "manual",
      },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    expect(response.status).toBe(201);
  });
});
