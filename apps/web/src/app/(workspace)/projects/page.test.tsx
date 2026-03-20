import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const controllerApiMocks = vi.hoisted(() => ({
  listVisibleProjects: vi.fn(),
}));

vi.mock("@/lib/controller-api", () => controllerApiMocks);

describe("ProjectsPage", () => {
  it("renders live project navigation from the controller-backed list", async () => {
    controllerApiMocks.listVisibleProjects.mockResolvedValue([
      {
        id: "proj_1",
        organization_id: "org_1",
        code: "P-1",
        name: "Project One",
        description: "Live project",
        status: "active",
        owner_user_id: "user_1",
        settings: {},
        counts: {
          annotation_queue: 4,
          risk_queue: 2,
          active_workflow_runs: 1,
          waiting_for_human_runs: 1,
        },
      },
    ]);

    const { default: ProjectsPage } = await import("./page");
    render(await ProjectsPage());

    expect(controllerApiMocks.listVisibleProjects).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("link", { name: "Open project" })).toHaveAttribute(
      "href",
      "/projects/proj_1",
    );
    expect(screen.getByRole("link", { name: "Annotation queue" })).toHaveAttribute(
      "href",
      "/projects/proj_1/annotation/queue",
    );
    expect(screen.getByRole("link", { name: "Risk dashboard" })).toHaveAttribute(
      "href",
      "/projects/proj_1/risk",
    );
    expect(screen.getByText("Project One")).toBeInTheDocument();
    expect(screen.getByText("Live project")).toBeInTheDocument();
  });
});
