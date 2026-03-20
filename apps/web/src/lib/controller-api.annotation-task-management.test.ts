import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const headersMock = vi.fn();
const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  headers: headersMock,
  cookies: cookiesMock,
}));

describe("annotation task management helpers", () => {
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

  it("creates annotation tasks through the live backend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            task: {
              id: "task_2",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              source_asset_id: "asset_1",
              task_type: "image_labeling",
              status: "queued",
              priority: 70,
              assigned_to_user_id: "user_annotator_1",
              reviewer_user_id: "user_reviewer_1",
              created_by_user_id: "user_pm_1",
              current_workflow_run_id: null,
              latest_ai_result_id: null,
              annotation_schema: {},
              input_payload: {},
              output_payload: {},
              claimed_at: null,
              due_at: null,
              submitted_at: null,
              reviewed_at: null,
              completed_at: null,
            },
          },
          meta: {
            request_id: "req_create",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { createAnnotationTask } = await import("./controller-api");
    const result = await createAnnotationTask(
      "proj_1",
      {
        source_asset_id: "asset_1",
        task_type: "image_labeling",
        priority: 70,
        assigned_to_user_id: "user_annotator_1",
        reviewer_user_id: "user_reviewer_1",
      },
      { idempotencyKey: "idem-create" },
    );

    expect(result.task?.id).toBe("task_2");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/annotation-tasks",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );
  });

  it("claims annotation tasks through the live backend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            task: {
              id: "task_1",
              status: "claimed",
            },
          },
          meta: {
            request_id: "req_claim",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { claimAnnotationTask } = await import("./controller-api");
    const result = await claimAnnotationTask("task_1", { idempotencyKey: "idem-claim" });

    expect(result.task?.status).toBe("claimed");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/annotation-tasks/task_1/claim",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );
  });

  it("patches annotation tasks through the live backend endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            task: {
              id: "task_1",
              status: "in_progress",
            },
          },
          meta: {
            request_id: "req_patch",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { updateAnnotationTask } = await import("./controller-api");
    const result = await updateAnnotationTask(
      "task_1",
      {
        priority: 80,
        due_at: "2026-03-20T01:15:00.000Z",
        assigned_to_user_id: "user_annotator_2",
        reviewer_user_id: "user_reviewer_2",
        status: "in_progress",
      },
      { idempotencyKey: "idem-patch" },
    );

    expect(result.task?.status).toBe("in_progress");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/annotation-tasks/task_1",
      expect.objectContaining({
        method: "PATCH",
        cache: "no-store",
      }),
    );
  });
});
