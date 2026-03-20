import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("catalog mutation forms", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("creates datasets through the platform api route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: { dataset: { id: "dataset_1" } },
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { DatasetMutationForm } = await import("./catalog-mutation-forms");
    render(<DatasetMutationForm projectId="proj_1" />);

    fireEvent.change(screen.getByLabelText("Dataset name"), {
      target: { value: "Incoming media" },
    });
    fireEvent.change(screen.getByLabelText("Source kind"), {
      target: { value: "manual" },
    });
    fireEvent.change(screen.getByLabelText("Dataset metadata"), {
      target: { value: "{\"owner\":\"pm\"}" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create dataset" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/proj_1/datasets",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(screen.getByText("Dataset saved. Refreshing the catalog.")).toBeInTheDocument();
    expect(refreshMock).toHaveBeenCalled();
  });

  it("updates datasets through the platform api route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { dataset: { id: "dataset_1" } } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { DatasetMutationForm } = await import("./catalog-mutation-forms");
    render(
      <DatasetMutationForm
        projectId="proj_1"
        dataset={{
          id: "dataset_1",
          project_id: "proj_1",
          name: "Incoming media",
          description: "Draft set",
          source_kind: "manual",
          status: "active",
          metadata: {},
          created_at: "2026-03-19T08:00:00Z",
          updated_at: "2026-03-19T08:00:00Z",
          archived_at: null,
        }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Dataset description"), {
      target: { value: "Updated draft set" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update dataset" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/datasets/dataset_1",
      expect.objectContaining({
        method: "PATCH",
      }),
    );
  });

  it("registers source assets through the platform api route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { source_asset: { id: "asset_1" } } }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { SourceAssetMutationForm } = await import("./catalog-mutation-forms");
    render(
      <SourceAssetMutationForm
        projectId="proj_1"
        datasets={[
          {
            id: "dataset_1",
            project_id: "proj_1",
            name: "Dataset One",
            description: null,
            source_kind: "manual",
            status: "active",
            metadata: {},
            created_at: "2026-03-19T08:00:00Z",
            updated_at: "2026-03-19T08:00:00Z",
            archived_at: null,
          },
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Asset kind"), {
      target: { value: "audio" },
    });
    fireEvent.change(screen.getByLabelText("Asset URI"), {
      target: { value: "https://example.com/media/1.wav" },
    });
    fireEvent.change(screen.getByLabelText("Dataset"), {
      target: { value: "dataset_1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Register source asset" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/proj_1/source-assets",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(screen.getByText("Source asset saved. Refreshing the catalog.")).toBeInTheDocument();
    expect(refreshMock).toHaveBeenCalled();
  });

  it("updates source assets through the platform api route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { source_asset: { id: "asset_1" } } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { SourceAssetMutationForm } = await import("./catalog-mutation-forms");
    render(
      <SourceAssetMutationForm
        projectId="proj_1"
        datasets={[]}
        asset={{
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
          metadata: {},
        }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Transcript"), {
      target: { value: "Updated transcript" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update source asset" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-assets/asset_1",
      expect.objectContaining({
        method: "PATCH",
      }),
    );
  });
});
