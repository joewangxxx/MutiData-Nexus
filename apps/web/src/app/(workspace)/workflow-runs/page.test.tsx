import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const controllerApiMocks = vi.hoisted(() => ({
  listWorkflowRuns: vi.fn(),
}));

const mockAdapterMocks = vi.hoisted(() => ({
  listWorkflowRuns: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => controllerApiMocks);
vi.mock("@/lib/mock-adapters", () => mockAdapterMocks);

describe("WorkflowRunsPage", () => {
  it("renders the live workflow run list from the controller API", async () => {
    const runs = [
      {
        id: "run_1",
        organization_id: "org_1",
        project_id: "proj_1",
        project_name: "Project One",
        workflow_domain: "risk_monitoring",
        workflow_type: "strategy_generate",
        source_entity_type: "risk_alert",
        source_entity_id: "alert_1",
        status: "running",
        priority: 90,
        requested_by_user_id: "user_pm_1",
        source: "frontend",
        correlation_key: "corr-1",
        idempotency_key: "idem-1",
        retry_of_run_id: null,
        input_snapshot: {},
        result_summary: {},
        error_code: null,
        error_message: null,
        started_at: "2026-03-19T08:00:00Z",
        completed_at: null,
        canceled_at: null,
        steps: [],
        coze_runs: [],
        ai_results: [],
      },
      {
        id: "run_2",
        organization_id: "org_1",
        project_id: "proj_1",
        project_name: "Project One",
        workflow_domain: "annotation",
        workflow_type: "ai_assist_generate",
        source_entity_type: "annotation_task",
        source_entity_id: "task_1",
        status: "waiting_for_human",
        priority: 70,
        requested_by_user_id: "user_annotator_1",
        source: "frontend",
        correlation_key: "corr-2",
        idempotency_key: "idem-2",
        retry_of_run_id: null,
        input_snapshot: {},
        result_summary: {},
        error_code: null,
        error_message: null,
        started_at: "2026-03-19T09:00:00Z",
        completed_at: null,
        canceled_at: null,
        steps: [],
        coze_runs: [],
        ai_results: [],
      },
      {
        id: "run_3",
        organization_id: "org_1",
        project_id: "proj_2",
        project_name: "Project Two",
        workflow_domain: "risk_monitoring",
        workflow_type: "strategy_generate",
        source_entity_type: "risk_alert",
        source_entity_id: "alert_2",
        status: "failed",
        priority: 60,
        requested_by_user_id: "user_pm_2",
        source: "frontend",
        correlation_key: "corr-3",
        idempotency_key: "idem-3",
        retry_of_run_id: null,
        input_snapshot: {},
        result_summary: {},
        error_code: "provider_timeout",
        error_message: "Coze response timed out.",
        started_at: "2026-03-19T10:00:00Z",
        completed_at: null,
        canceled_at: null,
        steps: [],
        coze_runs: [],
        ai_results: [],
      },
      {
        id: "run_4",
        organization_id: "org_1",
        project_id: "proj_2",
        project_name: "Project Two",
        workflow_domain: "annotation",
        workflow_type: "ai_assist_generate",
        source_entity_type: "annotation_task",
        source_entity_id: "task_2",
        status: "succeeded",
        priority: 50,
        requested_by_user_id: "user_annotator_2",
        source: "frontend",
        correlation_key: "corr-4",
        idempotency_key: "idem-4",
        retry_of_run_id: null,
        input_snapshot: {},
        result_summary: {},
        error_code: null,
        error_message: null,
        started_at: "2026-03-19T11:00:00Z",
        completed_at: "2026-03-19T11:05:00Z",
        canceled_at: null,
        steps: [],
        coze_runs: [],
        ai_results: [],
      },
    ];

    controllerApiMocks.listWorkflowRuns.mockResolvedValue(runs);
    mockAdapterMocks.listWorkflowRuns.mockResolvedValue(runs);

    const { default: WorkflowRunsPage } = await import("./page");
    render(await WorkflowRunsPage());

    expect(controllerApiMocks.listWorkflowRuns).toHaveBeenCalledWith();
    expect(mockAdapterMocks.listWorkflowRuns).not.toHaveBeenCalled();
    expect(screen.getAllByText("Project One")).toHaveLength(2);
    expect(screen.getAllByText("Project Two")).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /strategy generate/i })[0]).toHaveAttribute(
      "href",
      "/workflow-runs/run_1",
    );
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("Waiting for human")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Succeeded")).toBeInTheDocument();
  });
});
