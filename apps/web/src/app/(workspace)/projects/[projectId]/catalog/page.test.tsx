import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const navigationMock = vi.hoisted(() => ({
  notFound: vi.fn(),
  useRouter: vi.fn(() => ({
    refresh: vi.fn(),
  })),
}));

vi.mock("next/navigation", () => navigationMock);

const controllerApiMocks = vi.hoisted(() => ({
  isControllerApiError: vi.fn(() => false),
  getProject: vi.fn(),
  getSourceAssetAccess: vi.fn(),
  listProjectDatasets: vi.fn(),
  listProjectSourceAssets: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => controllerApiMocks);

describe("ProjectCatalogPage", () => {
  it("renders the project catalog from the controller API", async () => {
    controllerApiMocks.getProject.mockResolvedValue({
      id: "proj_1",
      organization_id: "org_1",
      code: "P-1",
      name: "Project One",
      description: "Live project",
      status: "active",
      owner_user_id: "user_1",
      settings: {},
      counts: {},
    });

    controllerApiMocks.listProjectDatasets.mockResolvedValue([
      {
        id: "dataset_1",
        project_id: "proj_1",
        name: "Operations Review",
        description: "Operational footage and references",
        source_kind: "workflow",
        status: "active",
        metadata: {},
        created_at: "2026-03-18T08:00:00Z",
        updated_at: "2026-03-18T09:00:00Z",
        archived_at: null,
      },
      {
        id: "dataset_2",
        project_id: "proj_1",
        name: "Media Intake",
        description: null,
        source_kind: "manual",
        status: "archived",
        metadata: {},
        created_at: "2026-03-17T08:00:00Z",
        updated_at: "2026-03-17T09:00:00Z",
        archived_at: "2026-03-18T10:00:00Z",
      },
    ]);

    controllerApiMocks.listProjectSourceAssets.mockResolvedValue([
      {
        id: "asset_1",
        project_id: "proj_1",
        dataset_id: "dataset_1",
        asset_kind: "image",
        uri: "https://example.com/assets/1.jpg",
        storage_key: "assets/1.jpg",
        mime_type: "image/jpeg",
        checksum: "sha256:asset1",
        duration_ms: null,
        width_px: 1920,
        height_px: 1080,
        frame_rate: null,
        transcript: null,
        metadata: { camera: "north" },
      },
      {
        id: "asset_2",
        project_id: "proj_1",
        dataset_id: "dataset_2",
        asset_kind: "video",
        uri: "https://example.com/assets/2.mp4",
        storage_key: "assets/2.mp4",
        mime_type: "video/mp4",
        checksum: "sha256:asset2",
        duration_ms: 15000,
        width_px: 1280,
        height_px: 720,
        frame_rate: 30,
        transcript: null,
        metadata: { camera: "east" },
      },
    ]);
    controllerApiMocks.getSourceAssetAccess.mockImplementation(async (assetId: string) => ({
      asset_id: assetId,
      project_id: "proj_1",
      dataset_id: assetId === "asset_1" ? "dataset_1" : "dataset_2",
      asset_kind: assetId === "asset_1" ? "image" : "video",
      delivery_type: "direct_uri",
      uri: `https://signed.example.com/${assetId}`,
      mime_type: assetId === "asset_1" ? "image/jpeg" : "video/mp4",
    }));

    const { default: ProjectCatalogPage } = await import("./page");
    render(await ProjectCatalogPage({ params: Promise.resolve({ projectId: "proj_1" }) }));

    expect(controllerApiMocks.getProject).toHaveBeenCalledWith("proj_1");
    expect(controllerApiMocks.listProjectDatasets).toHaveBeenCalledWith("proj_1");
    expect(controllerApiMocks.listProjectSourceAssets).toHaveBeenCalledWith("proj_1");
    expect(controllerApiMocks.getSourceAssetAccess).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("heading", { name: "Project One catalog" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create dataset" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Register source asset" })).toBeInTheDocument();
    expect(screen.getAllByText("Operations Review").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Media Intake").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("image").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("video").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Access entry")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open source URI" })[0]).toHaveAttribute(
      "href",
      "https://signed.example.com/asset_1",
    );
  });
});
