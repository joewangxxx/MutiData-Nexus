import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("ProjectMemberManagementPanel", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("shows actions for active members and hides them for inactive members", async () => {
    const { ProjectMemberManagementPanel } = await import("./project-member-management-panel");

    render(
      <ProjectMemberManagementPanel
        projectId="proj_1"
        members={[
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
          {
            id: "membership_2",
            project_id: "proj_1",
            user_id: "user_2",
            user: {
              id: "user_2",
              email: "observer@example.com",
              display_name: "Observer Two",
              status: "active",
            },
            project_role: "observer",
            status: "inactive",
            created_at: "2026-03-18T08:00:00Z",
            updated_at: "2026-03-18T08:10:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("Annotator One")).toBeInTheDocument();
    expect(screen.getByText("Observer Two")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Save changes" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Deactivate member" })).toHaveLength(1);
    expect(
      screen.getByText("Inactive member records are retained for auditability."),
    ).toBeInTheDocument();
  });

  it("submits member updates through the platform api route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            membership: {
              id: "membership_1",
              project_id: "proj_1",
              user_id: "user_1",
              user: {
                id: "user_1",
                email: "annotator@example.com",
                display_name: "Annotator One",
                status: "active",
              },
              project_role: "reviewer",
              status: "active",
              created_at: "2026-03-19T08:00:00Z",
              updated_at: "2026-03-19T08:10:00Z",
            },
          },
          meta: {
            request_id: "req_update",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { ProjectMemberManagementPanel } = await import("./project-member-management-panel");

    render(
      <ProjectMemberManagementPanel
        projectId="proj_1"
        members={[
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
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Role for Annotator One"), {
      target: { value: "reviewer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/proj_1/members/membership_1",
      expect.objectContaining({
        method: "PATCH",
        headers: expect.objectContaining({
          "content-type": "application/json",
        }),
      }),
    );
    await waitFor(() => {
      expect(refreshMock).toHaveBeenCalled();
    });
  });
});
