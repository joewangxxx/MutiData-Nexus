import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const updateProjectMemberMock = vi.fn();
const deleteProjectMemberMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  updateProjectMember: updateProjectMemberMock,
  deleteProjectMember: deleteProjectMemberMock,
  isControllerApiError: vi.fn(),
  serializeControllerApiError: serializeControllerApiErrorMock,
}));

describe("project member mutation routes", () => {
  beforeEach(() => {
    updateProjectMemberMock.mockReset();
    deleteProjectMemberMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  it("forwards member updates through the controller api helper with idempotency metadata", async () => {
    updateProjectMemberMock.mockResolvedValue({
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
    });

    const { PATCH } = await import("./route");
    const request = new NextRequest(
      "http://localhost/api/projects/proj_1/members/membership_1",
      {
        method: "PATCH",
        headers: {
          authorization: "Bearer token",
        },
        body: JSON.stringify({
          project_role: "reviewer",
          status: "active",
        }),
      },
    );

    const response = await PATCH(request, {
      params: Promise.resolve({ projectId: "proj_1", membershipId: "membership_1" }),
    });

    expect(updateProjectMemberMock).toHaveBeenCalledWith(
      "proj_1",
      "membership_1",
      {
        project_role: "reviewer",
        status: "active",
      },
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
        idempotencyKey: expect.stringContaining("project-member-update-membership_1"),
      }),
    );
    expect(response.status).toBe(200);
  });

  it("forwards member deletion through the controller api helper with idempotency metadata", async () => {
    deleteProjectMemberMock.mockResolvedValue({
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
        project_role: "annotator",
        status: "inactive",
        created_at: "2026-03-19T08:00:00Z",
        updated_at: "2026-03-19T08:10:00Z",
      },
    });

    const { DELETE } = await import("./route");
    const request = new NextRequest(
      "http://localhost/api/projects/proj_1/members/membership_1",
      {
        method: "DELETE",
        headers: {
          authorization: "Bearer token",
        },
      },
    );

    const response = await DELETE(request, {
      params: Promise.resolve({ projectId: "proj_1", membershipId: "membership_1" }),
    });

    expect(deleteProjectMemberMock).toHaveBeenCalledWith(
      "proj_1",
      "membership_1",
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
        idempotencyKey: expect.stringContaining("project-member-delete-membership_1"),
      }),
    );
    expect(response.status).toBe(200);
  });
});
