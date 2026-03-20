import { render, screen } from "@testing-library/react";

import { ShellFrame } from "./shell-frame";

describe("ShellFrame", () => {
  it("renders the shared navigation destinations for the workspace shell", () => {
    render(
      <ShellFrame
        activePath="/dashboard"
        currentProjectId="proj_atlas"
        currentUser={{
          id: "user_annotator_1",
          displayName: "Lin Chen",
          organizationName: "Nexus Ops",
          organizationRole: "project_manager",
        }}
      >
        <div>Dashboard content</div>
      </ShellFrame>,
    );

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Projects" })).toHaveAttribute(
      "href",
      "/projects",
    );
    expect(
      screen.getByRole("link", { name: "Workflow Runs" }),
    ).toHaveAttribute("href", "/workflow-runs");
    expect(screen.getByRole("link", { name: "Inbox" })).toHaveAttribute(
      "href",
      "/inbox",
    );
  });

  it("surfaces project-scoped wayfinding when a project is in context", () => {
    render(
      <ShellFrame
        activePath="/projects/proj_atlas/annotation/queue"
        currentProjectId="proj_atlas"
        currentUser={{
          id: "user_annotator_1",
          displayName: "Lin Chen",
          organizationName: "Nexus Ops",
          organizationRole: "annotator",
        }}
      >
        <div>Queue content</div>
      </ShellFrame>,
    );

    expect(screen.getByRole("link", { name: "Project Overview" })).toHaveAttribute(
      "href",
      "/projects/proj_atlas",
    );
    expect(screen.getByRole("link", { name: "Annotation Queue" })).toHaveAttribute(
      "href",
      "/projects/proj_atlas/annotation/queue",
    );
    expect(screen.getByRole("link", { name: "Risk Monitor" })).toHaveAttribute(
      "href",
      "/projects/proj_atlas/risk",
    );
    expect(screen.getByText("Queue content")).toBeInTheDocument();
  });
});
