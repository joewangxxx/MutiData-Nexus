import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listProjectMembersMock = vi.fn();
const serializeControllerApiErrorMock = vi.fn();

vi.mock("@/lib/controller-api", () => ({
  listProjectMembers: listProjectMembersMock,
  isControllerApiError: vi.fn(),
  serializeControllerApiError: serializeControllerApiErrorMock,
}));

describe("project members list route", () => {
  beforeEach(() => {
    listProjectMembersMock.mockReset();
    serializeControllerApiErrorMock.mockReset();
  });

  it("forwards member list requests through the controller api helper", async () => {
    listProjectMembersMock.mockResolvedValue([
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

    const { GET } = await import("./route");
    const request = new NextRequest("http://localhost/api/projects/proj_1/members", {
      method: "GET",
      headers: {
        authorization: "Bearer token",
        cookie: "session=abc123",
        "x-request-id": "req-abc123",
      },
    });

    const response = await GET(request, {
      params: Promise.resolve({ projectId: "proj_1" }),
    });

    expect(listProjectMembersMock).toHaveBeenCalledWith(
      "proj_1",
      expect.objectContaining({
        requestHeaders: expect.any(Headers),
      }),
    );
    const requestHeaders = listProjectMembersMock.mock.calls[0][1]?.requestHeaders as Headers;
    expect(requestHeaders.get("authorization")).toBe("Bearer token");
    expect(requestHeaders.get("cookie")).toBe("session=abc123");
    expect(requestHeaders.get("x-request-id")).toBe("req-abc123");
    expect(response.status).toBe(200);
  });
});
