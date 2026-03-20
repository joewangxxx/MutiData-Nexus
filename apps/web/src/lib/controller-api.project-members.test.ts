import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const headersMock = vi.fn();
const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  headers: headersMock,
  cookies: cookiesMock,
}));

describe("project member controller api helpers", () => {
  beforeEach(() => {
    process.env.CONTROLLER_API_URL = "http://backend.test";
    headersMock.mockReturnValue(
      new Headers({
        authorization: "Bearer user-123",
        "x-request-id": "req-123",
      }),
    );
    cookiesMock.mockReturnValue({
      toString: () => "session=abc123",
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    delete process.env.CONTROLLER_API_URL;
  });

  it("lists project members with nested user summaries from the live contract endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [
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
          ],
          meta: {
            request_id: "req_members",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { listProjectMembers } = await import("./controller-api");
    const members = await listProjectMembers("proj_1");

    expect(members).toHaveLength(1);
    expect(members[0].user.display_name).toBe("Annotator One");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/members",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("uses the runtime auth token while preserving explicit request headers on member mutations", async () => {
    process.env.CONTROLLER_API_AUTH_TOKEN = "00000000-0000-0000-0000-000000000321";
    headersMock.mockReturnValue(new Headers({}));
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
            request_id: "req_members_update",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { updateProjectMember } = await import("./controller-api");
    await updateProjectMember(
      "proj_1",
      "membership_1",
      {
        project_role: "reviewer",
        status: "active",
      },
      {
        requestHeaders: new Headers({
          cookie: "session=explicit",
          "x-request-id": "req-explicit",
        }),
      },
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    const headers = requestInit?.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer 00000000-0000-0000-0000-000000000321");
    expect(headers.get("cookie")).toBe("session=explicit");
    expect(headers.get("x-request-id")).toBe("req-explicit");
    expect(headers.get("Idempotency-Key")).toBe("project-member-update-membership_1-uuid-fixed");
  });

  it("adds an idempotency key for project member update mutations", async () => {
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
            request_id: "req_members_update",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { updateProjectMember } = await import("./controller-api");
    await updateProjectMember(
      "proj_1",
      "membership_1",
      {
        project_role: "reviewer",
        status: "active",
      },
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/members/membership_1",
      expect.objectContaining({
        method: "PATCH",
        cache: "no-store",
      }),
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "project-member-update-membership_1-uuid-fixed",
    );
  });

  it("adds an idempotency key for project member deletion mutations", async () => {
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
              project_role: "annotator",
              status: "inactive",
              created_at: "2026-03-19T08:00:00Z",
              updated_at: "2026-03-19T08:10:00Z",
            },
          },
          meta: {
            request_id: "req_members_delete",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("crypto", {
      randomUUID: () => "uuid-fixed",
    });

    const { deleteProjectMember } = await import("./controller-api");
    await deleteProjectMember("proj_1", "membership_1");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/members/membership_1",
      expect.objectContaining({
        method: "DELETE",
        cache: "no-store",
      }),
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "project-member-delete-membership_1-uuid-fixed",
    );
  });
});
