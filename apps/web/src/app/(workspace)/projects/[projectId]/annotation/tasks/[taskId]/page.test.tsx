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
  getAnnotationWorkbench: vi.fn(),
  getSourceAssetAccess: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => controllerApiMocks);

describe("AnnotationTaskPage", () => {
  it("renders a unified media preview from backend source asset access", async () => {
    controllerApiMocks.getAnnotationWorkbench.mockResolvedValue({
      project: {
        id: "proj_1",
        organization_id: "org_1",
        code: "P-1",
        name: "Project One",
        description: "Live project",
        status: "active",
        owner_user_id: "user_1",
        settings: {},
        counts: {},
      },
      task: {
        id: "task_1",
        project_id: "proj_1",
        dataset_id: "dataset_1",
        source_asset_id: "asset_1",
        task_type: "annotation",
        status: "in_progress",
        priority: 80,
        assigned_to_user_id: "user_annotator_1",
        reviewer_user_id: "user_reviewer_1",
        created_by_user_id: "user_pm_1",
        current_workflow_run_id: "run_1",
        latest_ai_result_id: "ai_1",
        annotation_schema: {},
        input_payload: {},
        output_payload: {},
        claimed_at: null,
        due_at: null,
        submitted_at: null,
        reviewed_at: null,
        completed_at: null,
      },
      sourceAsset: {
        id: "asset_1",
        project_id: "proj_1",
        dataset_id: "dataset_1",
        asset_kind: "video",
        uri: "https://example.com/assets/asset_1.mp4",
        storage_key: "assets/asset_1.mp4",
        mime_type: "video/mp4",
        checksum: "sha256:asset_1",
        duration_ms: 30000,
        width_px: 1920,
        height_px: 1080,
        frame_rate: 30,
        transcript: "Seed transcript",
        metadata: {},
      },
      revisions: [],
      reviews: [],
      aiSuggestions: [],
      linkedRun: {
        id: "run_1",
        organization_id: "org_1",
        project_id: "proj_1",
        workflow_domain: "annotation",
        workflow_type: "ai_assist_generate",
        source_entity_type: "annotation_task",
        source_entity_id: "task_1",
        status: "waiting_for_human",
        priority: 80,
        requested_by_user_id: "user_annotator_1",
        source: "frontend",
        correlation_key: "corr-1",
        idempotency_key: "idem-1",
        retry_of_run_id: null,
        input_snapshot: {},
        result_summary: {},
        error_code: null,
        error_message: null,
        started_at: "2026-03-18T08:00:00Z",
        completed_at: null,
        canceled_at: null,
        steps: [],
        coze_runs: [],
        ai_results: [],
      },
    });
    controllerApiMocks.getSourceAssetAccess.mockResolvedValue({
      asset_id: "asset_1",
      project_id: "proj_1",
      dataset_id: "dataset_1",
      asset_kind: "video",
      delivery_type: "direct_uri",
      uri: "https://signed.example.com/assets/asset_1.mp4",
      mime_type: "video/mp4",
    });

    const { default: AnnotationTaskPage } = await import("./page");
    render(await AnnotationTaskPage({ params: Promise.resolve({ projectId: "proj_1", taskId: "task_1" }) }));

    expect(controllerApiMocks.getAnnotationWorkbench).toHaveBeenCalledWith("proj_1", "task_1");
    expect(controllerApiMocks.getSourceAssetAccess).toHaveBeenCalledWith("asset_1");
    expect(screen.getByRole("heading", { name: "Unified media preview" })).toBeInTheDocument();
    expect(screen.getByLabelText("Video preview for asset_1")).toHaveAttribute(
      "src",
      "https://signed.example.com/assets/asset_1.mp4",
    );
    expect(screen.getByText("Seed transcript")).toBeInTheDocument();
  });
});
