import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const headersMock = vi.fn();
const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  headers: headersMock,
  cookies: cookiesMock,
}));

describe("catalog management controller api helpers", () => {
  beforeEach(() => {
    process.env.CONTROLLER_API_URL = "http://backend.test";
    headersMock.mockReturnValue(new Headers());
    cookiesMock.mockReturnValue({
      toString: () => "",
    });
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    delete process.env.CONTROLLER_API_URL;
  });

  it("creates project datasets through the controller api", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            dataset: {
              id: "dataset_1",
              project_id: "proj_1",
              name: "Incoming media",
              description: "Draft set",
              source_kind: "manual",
              status: "active",
              metadata: { owner: "pm" },
              created_at: "2026-03-19T08:00:00Z",
              updated_at: "2026-03-19T08:00:00Z",
              archived_at: null,
            },
          },
          meta: {
            request_id: "req_dataset_create",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { createProjectDataset } = await import("./controller-api");
    const result = await createProjectDataset("proj_1", {
      name: "Incoming media",
      source_kind: "manual",
      description: "Draft set",
      metadata: { owner: "pm" },
    });

    expect(result.dataset?.id).toBe("dataset_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/datasets",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );
    const requestInit = fetchMock.mock.calls[0][1];
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "dataset-create-proj_1-uuid-fixed",
    );
  });

  it("updates datasets through the controller api", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            dataset: {
              id: "dataset_1",
              project_id: "proj_1",
              name: "Incoming media",
              description: "Updated draft set",
              source_kind: "manual",
              status: "active",
              metadata: { owner: "pm" },
              created_at: "2026-03-19T08:00:00Z",
              updated_at: "2026-03-19T09:00:00Z",
              archived_at: null,
            },
          },
          meta: {
            request_id: "req_dataset_patch",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { updateDataset } = await import("./controller-api");
    const result = await updateDataset("dataset_1", {
      name: "Incoming media",
      description: "Updated draft set",
      source_kind: "manual",
      metadata: { owner: "pm" },
    });

    expect(result.dataset?.updated_at).toBe("2026-03-19T09:00:00Z");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/datasets/dataset_1",
      expect.objectContaining({
        method: "PATCH",
        cache: "no-store",
      }),
    );
    const requestInit = fetchMock.mock.calls[0][1];
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "dataset-update-dataset_1-uuid-fixed",
    );
  });

  it("registers source assets through the controller api", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            source_asset: {
              id: "asset_1",
              project_id: "proj_1",
              dataset_id: null,
              asset_kind: "audio",
              uri: "https://example.com/media/1.wav",
              storage_key: "media/1.wav",
              mime_type: "audio/wav",
              checksum: "sha256:asset1",
              duration_ms: 12000,
              width_px: null,
              height_px: null,
              frame_rate: null,
              transcript: "Transcript",
              metadata: { speaker: "a" },
            },
          },
          meta: {
            request_id: "req_asset_create",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { registerProjectSourceAsset } = await import("./controller-api");
    const result = await registerProjectSourceAsset("proj_1", {
      asset_kind: "audio",
      uri: "https://example.com/media/1.wav",
      metadata: { speaker: "a" },
    });

    expect(result.source_asset?.id).toBe("asset_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/source-assets",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );
    const requestInit = fetchMock.mock.calls[0][1];
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "source-asset-create-proj_1-uuid-fixed",
    );
  });

  it("updates source assets through the controller api", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            source_asset: {
              id: "asset_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              asset_kind: "audio",
              uri: "https://example.com/media/1.wav",
              storage_key: "media/1.wav",
              mime_type: "audio/wav",
              checksum: "sha256:asset1",
              duration_ms: 12000,
              width_px: null,
              height_px: null,
              frame_rate: null,
              transcript: "Updated transcript",
              metadata: { speaker: "a" },
            },
          },
          meta: {
            request_id: "req_asset_patch",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { updateSourceAsset } = await import("./controller-api");
    const result = await updateSourceAsset("asset_1", {
      dataset_id: "dataset_1",
      transcript: "Updated transcript",
      metadata: { speaker: "a" },
    });

    expect(result.source_asset?.transcript).toBe("Updated transcript");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/source-assets/asset_1",
      expect.objectContaining({
        method: "PATCH",
        cache: "no-store",
      }),
    );
    const requestInit = fetchMock.mock.calls[0][1];
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "source-asset-update-asset_1-uuid-fixed",
    );
  });
});
