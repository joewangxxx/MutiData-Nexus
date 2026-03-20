import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const navigationMock = vi.hoisted(() => ({
  useRouter: vi.fn(() => ({
    refresh: vi.fn(),
  })),
}));

vi.mock("next/navigation", () => navigationMock);

const controllerApiMocks = vi.hoisted(() => ({
  getProjectRiskOverview: vi.fn(),
  isControllerApiError: vi.fn(() => false),
}));

vi.mock("@/lib/controller-api", () => controllerApiMocks);

describe("ProjectRiskPage", () => {
  it("renders the shared risk capture form inside the current project page", async () => {
    controllerApiMocks.getProjectRiskOverview.mockResolvedValue({
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
      alerts: [],
      signals: [],
    });

    const { default: ProjectRiskPage } = await import("./page");

    render(await ProjectRiskPage({ params: Promise.resolve({ projectId: "proj_1" }) }));

    expect(screen.getByRole("link", { name: "Back to project" })).toHaveAttribute(
      "href",
      "/projects/proj_1",
    );
    expect(screen.getByLabelText("Source kind")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save signal only" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save and analyze" })).toBeInTheDocument();
  });
});
