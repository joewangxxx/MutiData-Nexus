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
  getProjectDashboard: vi.fn(),
  listAnnotationTasks: vi.fn(),
  listRiskAlerts: vi.fn(),
  listWorkflowRuns: vi.fn(),
  getProjectMembers: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => controllerApiMocks);

describe("ProjectOverviewPage", () => {
  it("links into the project catalog from the overview page", async () => {
    controllerApiMocks.getProjectDashboard.mockResolvedValue({
      project: {
        id: "proj_1",
        organization_id: "org_1",
        code: "P-1",
        name: "Project One",
        description: "Live project",
        status: "active",
        owner_user_id: "user_1",
        settings: {},
        counts: {
          annotation_queue: 1,
          risk_queue: 1,
          active_workflow_runs: 1,
          waiting_for_human_runs: 0,
        },
      },
      queues: { annotation: 1, risk: 1 },
      workload: {
        active_runs: 1,
        waiting_for_human: 0,
        waiting_for_coze: 0,
        failures_last_24h: 0,
      },
      inbox: {
        assigned_tasks: 0,
        open_alerts: 0,
        pending_approvals: 0,
      },
      recent_activity: [],
    });
    controllerApiMocks.listAnnotationTasks.mockResolvedValue([]);
    controllerApiMocks.listRiskAlerts.mockResolvedValue([]);
    controllerApiMocks.listWorkflowRuns.mockResolvedValue([]);
    controllerApiMocks.getProjectMembers.mockResolvedValue([
      {
        id: "membership_1",
        project_id: "proj_1",
        user_id: "user_1",
        user: {
          id: "user_1",
          email: "annotator@example.com",
          display_name: "Annotator One",
          status: "active",
        },
        project_role: "annotator",
        status: "active",
        created_at: "2026-03-19T08:00:00Z",
        updated_at: "2026-03-19T08:10:00Z",
      },
    ]);

    const { default: ProjectOverviewPage } = await import("./page");
    render(await ProjectOverviewPage({ params: Promise.resolve({ projectId: "proj_1" }) }));

    expect(screen.getByRole("link", { name: "Open catalog" })).toHaveAttribute(
      "href",
      "/projects/proj_1/catalog",
    );
    expect(screen.getByText("Project members")).toBeInTheDocument();
    expect(screen.getByText("Annotator One")).toBeInTheDocument();
  });
});
