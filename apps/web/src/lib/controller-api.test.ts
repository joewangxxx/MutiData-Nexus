import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const headersMock = vi.fn();
const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  headers: headersMock,
  cookies: cookiesMock,
}));

describe("controller api helpers", () => {
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
    delete process.env.CONTROLLER_API_AUTH_TOKEN;
  });

  it("uses the server runtime auth token when request authorization is absent", async () => {
    process.env.CONTROLLER_API_AUTH_TOKEN = "00000000-0000-0000-0000-000000000321";
    headersMock.mockReturnValue(
      new Headers({
        "x-request-id": "req-no-auth",
      }),
    );

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
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
              risk_queue: 0,
              active_workflow_runs: 1,
              waiting_for_human_runs: 1,
            },
          },
          meta: {
            request_id: "req_project",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { getProject } = await import("./controller-api");
    await getProject("proj_1");

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    const headers = requestInit?.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer 00000000-0000-0000-0000-000000000321");
    expect(headers.get("cookie")).toBe("session=abc123");
    expect(headers.get("x-request-id")).toBe("req-no-auth");
  });

  it("lists visible projects from the live controller endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [
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
          ],
          meta: {
            request_id: "req_projects",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { listVisibleProjects } = await import("./controller-api");
    const projects = await listVisibleProjects();

    expect(projects).toHaveLength(1);
    expect(projects[0].id).toBe("proj_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("prefers the incoming authorization header over the server runtime auth token", async () => {
    process.env.CONTROLLER_API_AUTH_TOKEN = "00000000-0000-0000-0000-000000000321";

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
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
              risk_queue: 0,
              active_workflow_runs: 1,
              waiting_for_human_runs: 1,
            },
          },
          meta: {
            request_id: "req_project",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { getProject } = await import("./controller-api");
    await getProject("proj_1");

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("authorization")).toBe("Bearer user-123");
  });

  it("builds the annotation queue model from live contract endpoints", async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
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
                risk_queue: 0,
                active_workflow_runs: 1,
                waiting_for_human_runs: 1,
              },
            },
            meta: {
              request_id: "req_project",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "task_1",
                project_id: "proj_1",
                dataset_id: "dataset_1",
                source_asset_id: "asset_1",
                task_type: "issue_summary",
                status: "claimed",
                priority: 80,
                assigned_to_user_id: "user_annotator_1",
                reviewer_user_id: "user_reviewer_1",
                created_by_user_id: "user_pm_1",
                current_workflow_run_id: "run_1",
                latest_ai_result_id: "ai_1",
                annotation_schema: {},
                input_payload: {},
                output_payload: {},
                claimed_at: null,
                due_at: null,
                submitted_at: null,
                reviewed_at: null,
                completed_at: null,
              },
            ],
            meta: {
              request_id: "req_tasks",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              id: "asset_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              asset_kind: "audio",
              uri: "https://example.com/assets/1.wav",
              storage_key: "assets/1.wav",
              mime_type: "audio/wav",
              checksum: "sha256:asset1",
              duration_ms: 12000,
              width_px: null,
              height_px: null,
              frame_rate: null,
              transcript: "Seed transcript",
              metadata: {},
            },
            meta: {
              request_id: "req_asset",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const { getProjectAnnotationQueue } = await import("./controller-api");
    const queue = await getProjectAnnotationQueue("proj_1");

    expect(queue.project.id).toBe("proj_1");
    expect(queue.tasks).toHaveLength(1);
    expect(queue.tasks[0].status).toBe("claimed");
    expect(queue.tasks[0].source_asset?.asset_kind).toBe("audio");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://backend.test/api/v1/projects/proj_1",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://backend.test/api/v1/projects/proj_1/annotation-tasks?limit=20",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://backend.test/api/v1/source-assets/asset_1",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("adds an idempotency key for annotation review mutations", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            review: {
              id: "review_1",
              annotation_task_id: "task_1",
              revision_id: "rev_2",
              reviewed_by_user_id: "user_reviewer_1",
              decision: "approve",
              notes: "Looks good",
              created_at: "2026-03-19T10:00:00Z",
            },
            task: {
              id: "task_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              source_asset_id: "asset_1",
              task_type: "image_labeling",
              status: "approved",
              priority: 5,
              assigned_to_user_id: "user_annotator_1",
              reviewer_user_id: "user_reviewer_1",
              created_by_user_id: "user_pm_1",
              current_workflow_run_id: "run_1",
              latest_ai_result_id: "ai_1",
              annotation_schema: {},
              input_payload: {},
              output_payload: {},
              claimed_at: null,
              due_at: null,
              submitted_at: "2026-03-19T09:00:00Z",
              reviewed_at: "2026-03-19T10:00:00Z",
              completed_at: "2026-03-19T10:00:00Z",
            },
          },
          meta: {
            request_id: "req_review",
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

    const { requestAnnotationReview } = await import("./controller-api");
    await requestAnnotationReview("task_1", {
      revision_id: "rev_2",
      decision: "approve",
      notes: "Looks good",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/annotation-tasks/task_1/reviews",
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers),
      }),
    );

    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Idempotency-Key")).toBe("annotation-review-task_1-uuid-fixed");
  });

  it("builds the annotation workbench model from live contract endpoints", async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
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
                risk_queue: 0,
                active_workflow_runs: 1,
                waiting_for_human_runs: 1,
              },
            },
            meta: {
              request_id: "req_project",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              id: "task_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              source_asset_id: "asset_1",
              task_type: "issue_summary",
              status: "submitted",
              priority: 80,
              assigned_to_user_id: "user_annotator_1",
              reviewer_user_id: "user_reviewer_1",
              created_by_user_id: "user_pm_1",
              current_workflow_run_id: "run_1",
              latest_ai_result_id: "ai_1",
              annotation_schema: {},
              input_payload: {},
              output_payload: {},
              claimed_at: null,
              due_at: null,
              submitted_at: null,
              reviewed_at: null,
              completed_at: null,
            },
            meta: {
              request_id: "req_task",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              id: "asset_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              asset_kind: "audio",
              uri: "https://example.com/assets/1.wav",
              storage_key: "assets/1.wav",
              mime_type: "audio/wav",
              checksum: "sha256:asset1",
              duration_ms: 12000,
              width_px: null,
              height_px: null,
              frame_rate: null,
              transcript: "Seed transcript",
              metadata: {},
            },
            meta: {
              request_id: "req_asset",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "rev_1",
                annotation_task_id: "task_1",
                revision_no: 1,
                revision_kind: "submission",
                source_ai_result_id: "ai_1",
                created_by_user_id: "user_annotator_1",
                labels: ["label_a"],
                content: { summary: "Draft" },
                review_notes: null,
                confidence_score: 0.9,
                created_at: "2026-03-18T08:00:00Z",
              },
            ],
            meta: {
              request_id: "req_revisions",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "ai_1",
                workflow_run_id: "run_1",
                coze_run_id: "coze_1",
                result_type: "annotation_suggestion",
                status: "waiting_for_human",
                source_entity_type: "annotation_task",
                source_entity_id: "task_1",
                raw_payload: {},
                normalized_payload: {},
                reviewed_by_user_id: null,
                review_notes: null,
                reviewed_at: null,
                applied_by_user_id: null,
                applied_at: null,
              },
            ],
            meta: {
              request_id: "req_ai",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "review_1",
                annotation_task_id: "task_1",
                revision_id: "rev_1",
                reviewed_by_user_id: "user_reviewer_1",
                decision: "approve",
                notes: "Looks good",
                created_at: "2026-03-18T08:20:00Z",
              },
            ],
            meta: {
              request_id: "req_reviews",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              id: "run_1",
              organization_id: "org_1",
              project_id: "proj_1",
              workflow_domain: "annotation",
              workflow_type: "ai_assist_generate",
              source_entity_type: "annotation_task",
              source_entity_id: "task_1",
              status: "waiting_for_human",
              priority: 80,
              requested_by_user_id: "user_annotator_1",
              source: "frontend",
              correlation_key: "corr-1",
              idempotency_key: "idem-1",
              retry_of_run_id: null,
              input_snapshot: {},
              result_summary: {},
              error_code: null,
              error_message: null,
              started_at: "2026-03-18T08:00:00Z",
              completed_at: null,
              canceled_at: null,
              steps: [],
              coze_runs: [],
              ai_results: [],
            },
            meta: {
              request_id: "req_run",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const { getAnnotationWorkbench } = await import("./controller-api");
    const workbench = await getAnnotationWorkbench("proj_1", "task_1");

    expect(workbench.project.id).toBe("proj_1");
    expect(workbench.task.id).toBe("task_1");
    expect(workbench.sourceAsset.asset_kind).toBe("audio");
    expect(workbench.revisions).toHaveLength(1);
    expect(workbench.aiSuggestions).toHaveLength(1);
    expect(workbench.reviews).toHaveLength(1);
    expect(workbench.linkedRun?.id).toBe("run_1");
  });

  it("loads annotation review history and records reviewer decisions", async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "review_2",
                annotation_task_id: "task_1",
                revision_id: "rev_2",
                reviewed_by_user_id: "user_reviewer_1",
                decision: "reject",
                notes: "Needs another pass",
                created_at: "2026-03-18T08:30:00Z",
              },
              {
                id: "review_1",
                annotation_task_id: "task_1",
                revision_id: "rev_1",
                reviewed_by_user_id: "user_reviewer_1",
                decision: "approve",
                notes: "Looks good",
                created_at: "2026-03-18T08:00:00Z",
              },
            ],
            meta: {
              request_id: "req_reviews",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              review: {
                id: "review_3",
                annotation_task_id: "task_1",
                revision_id: "rev_2",
                reviewed_by_user_id: "user_reviewer_1",
                decision: "revise",
                notes: "Please tighten the labels.",
                created_at: "2026-03-18T09:00:00Z",
              },
              task: {
                id: "task_1",
                project_id: "proj_1",
                dataset_id: "dataset_1",
                source_asset_id: "asset_1",
                task_type: "issue_summary",
                status: "needs_review",
                priority: 60,
                assigned_to_user_id: "user_annotator_1",
                reviewer_user_id: "user_reviewer_1",
                created_by_user_id: "user_pm_1",
                current_workflow_run_id: "run_1",
                latest_ai_result_id: "ai_1",
                annotation_schema: {},
                input_payload: {},
                output_payload: {},
                claimed_at: null,
                due_at: null,
                submitted_at: null,
                reviewed_at: "2026-03-18T09:00:00Z",
                completed_at: null,
              },
            },
            meta: {
              request_id: "req_review_submit",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const reviews = await controllerApi.getAnnotationTaskReviews("task_1");

    expect(reviews[0].id).toBe("review_2");
    expect(reviews[0].decision).toBe("reject");

    const result = await controllerApi.requestAnnotationReview("task_1", {
      revision_id: "rev_2",
      decision: "revise",
      notes: "Please tighten the labels.",
    });

    expect(result.review?.id).toBe("review_3");
    expect(result.task?.status).toBe("needs_review");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://backend.test/api/v1/annotation-tasks/task_1/reviews",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://backend.test/api/v1/annotation-tasks/task_1/reviews",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );
  });

  it("submits annotation revisions with idempotency metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            ai_result: { id: "ai_1" },
          },
          meta: {
            request_id: "req_submit",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { submitAnnotationRevision } = await import("./controller-api");
    const result = await submitAnnotationRevision("task_1", {
      labels: ["label_a", "label_b"],
      content: { summary: "Submitted" },
      review_notes: "Looks good",
      confidence_score: 0.88,
    });

    expect(result.workflow_run.id).toBe("run_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/annotation-tasks/task_1/submissions",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toContain(
      "task_1",
    );
  });

  it("surfaces contract errors with their code and status", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "not_found",
            message: "Task not found.",
            details: [],
          },
        }),
        { status: 404, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { getAnnotationTask } = await import("./controller-api");

    await expect(getAnnotationTask("task_missing")).rejects.toMatchObject({
      code: "not_found",
      status: 404,
    });
  });

  it("builds the project risk overview from live contract endpoints", async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
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
            meta: {
              request_id: "req_project",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "alert_2",
                project_id: "proj_1",
                risk_signal_id: "signal_2",
                status: "escalated",
                severity: 95,
                title: "Second alert",
                summary: "Needs attention",
                assigned_to_user_id: null,
                detected_by_workflow_run_id: "run_2",
                next_review_at: null,
                resolved_at: null,
              },
              {
                id: "alert_1",
                project_id: "proj_1",
                risk_signal_id: "signal_1",
                status: "open",
                severity: 60,
                title: "First alert",
                summary: "Watch closely",
                assigned_to_user_id: "user_pm_1",
                detected_by_workflow_run_id: "run_1",
                next_review_at: null,
                resolved_at: null,
              },
            ],
            meta: {
              request_id: "req_alerts",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "signal_2",
                project_id: "proj_1",
                source_kind: "workflow",
                signal_type: "coze_latency",
                severity: 90,
                status: "active",
                title: "Later signal",
                description: "Second",
                signal_payload: {},
                observed_at: "2026-03-18T09:00:00Z",
                created_by_user_id: "user_pm_1",
              },
              {
                id: "signal_1",
                project_id: "proj_1",
                source_kind: "workflow",
                signal_type: "annotation_backlog",
                severity: 65,
                status: "active",
                title: "Earlier signal",
                description: "First",
                signal_payload: {},
                observed_at: "2026-03-18T08:00:00Z",
                created_by_user_id: "user_pm_1",
              },
            ],
            meta: {
              request_id: "req_signals",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const dashboard = await controllerApi.getProjectRiskOverview("proj_1");

    expect(dashboard.project.id).toBe("proj_1");
    expect(dashboard.alerts[0].id).toBe("alert_2");
    expect(dashboard.signals[0].id).toBe("signal_2");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("loads the project dashboard from the live contract endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
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
            queues: {
              annotation: 12,
              risk: 3,
            },
            workload: {
              active_runs: 4,
              waiting_for_human: 2,
              waiting_for_coze: 1,
              failures_last_24h: 0,
            },
            inbox: {
              assigned_tasks: 2,
              open_alerts: 3,
              pending_approvals: 1,
            },
            recent_activity: [],
          },
          meta: {
            request_id: "req_dashboard",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const dashboard = await controllerApi.getProjectDashboard("proj_1");

    expect(dashboard.project.id).toBe("proj_1");
    expect(dashboard.queues.risk).toBe(3);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/dashboard",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("lists project datasets from the live contract endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [
            {
              id: "dataset_2",
              project_id: "proj_1",
              name: "Media Intake",
              description: "Incoming source material",
              source_kind: "manual",
              status: "active",
              metadata: {},
              created_at: "2026-03-18T08:00:00Z",
              updated_at: "2026-03-18T08:30:00Z",
              archived_at: null,
            },
            {
              id: "dataset_1",
              project_id: "proj_1",
              name: "Ops Review",
              description: null,
              source_kind: "workflow",
              status: "archived",
              metadata: {},
              created_at: "2026-03-17T08:00:00Z",
              updated_at: "2026-03-17T08:30:00Z",
              archived_at: "2026-03-18T09:00:00Z",
            },
          ],
          meta: {
            request_id: "req_datasets",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { listProjectDatasets } = await import("./controller-api");
    const datasets = await listProjectDatasets("proj_1");

    expect(datasets).toHaveLength(2);
    expect(datasets[0].id).toBe("dataset_2");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/datasets?limit=50",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("lists project source assets from the live contract endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [
            {
              id: "asset_2",
              project_id: "proj_1",
              dataset_id: "dataset_2",
              asset_kind: "video",
              uri: "https://example.com/assets/2.mp4",
              storage_key: "assets/2.mp4",
              mime_type: "video/mp4",
              checksum: "sha256:asset2",
              duration_ms: 15000,
              width_px: 1920,
              height_px: 1080,
              frame_rate: 30,
              transcript: null,
              metadata: {},
            },
            {
              id: "asset_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              asset_kind: "image",
              uri: "https://example.com/assets/1.jpg",
              storage_key: "assets/1.jpg",
              mime_type: "image/jpeg",
              checksum: "sha256:asset1",
              duration_ms: null,
              width_px: 1200,
              height_px: 800,
              frame_rate: null,
              transcript: null,
              metadata: {},
            },
          ],
          meta: {
            request_id: "req_assets",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { listProjectSourceAssets } = await import("./controller-api");
    const assets = await listProjectSourceAssets("proj_1");

    expect(assets).toHaveLength(2);
    expect(assets[0].id).toBe("asset_2");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/projects/proj_1/source-assets?limit=50",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("requests source asset access from the backend-owned access endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            access: {
              asset_id: "asset_1",
              project_id: "proj_1",
              dataset_id: "dataset_1",
              asset_kind: "image",
              delivery_type: "direct_uri",
              uri: "https://signed.example.com/asset_1",
              mime_type: "image/jpeg",
            },
          },
          meta: {
            request_id: "req_access",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { getSourceAssetAccess } = await import("./controller-api");
    const access = await getSourceAssetAccess("asset_1");

    expect(access.asset_id).toBe("asset_1");
    expect(access.uri).toBe("https://signed.example.com/asset_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/source-assets/asset_1/access",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );
  });

  it("lists workflow runs with project and domain filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: [
            {
              id: "run_2",
              organization_id: "org_1",
              project_id: "proj_1",
              workflow_domain: "risk_monitoring",
              workflow_type: "strategy_generate",
              source_entity_type: "risk_alert",
              source_entity_id: "alert_1",
              status: "running",
              priority: 60,
              requested_by_user_id: "user_pm_1",
              source: "frontend",
              correlation_key: "corr-2",
              idempotency_key: "idem-2",
              retry_of_run_id: null,
              input_snapshot: {},
              result_summary: {},
              error_code: null,
              error_message: null,
              started_at: "2026-03-18T09:00:00Z",
              completed_at: null,
              canceled_at: null,
              steps: [],
              coze_runs: [],
              ai_results: [],
            },
          ],
          meta: {
            request_id: "req_runs",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const runs = await controllerApi.listWorkflowRuns({
      projectId: "proj_1",
      workflowDomain: "risk_monitoring",
      limit: 4,
    });

    expect(runs[0].id).toBe("run_2");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/workflow-runs?project_id=proj_1&workflow_domain=risk_monitoring&limit=4",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("hydrates workflow run project names from visible project details", async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: [
              {
                id: "run_2",
                organization_id: "org_1",
                project_id: "proj_1",
                workflow_domain: "risk_monitoring",
                workflow_type: "strategy_generate",
                source_entity_type: "risk_alert",
                source_entity_id: "alert_1",
                status: "running",
                priority: 60,
                requested_by_user_id: "user_pm_1",
                source: "frontend",
                correlation_key: "corr-2",
                idempotency_key: "idem-2",
                retry_of_run_id: null,
                input_snapshot: {},
                result_summary: {},
                error_code: null,
                error_message: null,
                started_at: "2026-03-18T09:00:00Z",
                completed_at: null,
                canceled_at: null,
                steps: [],
                coze_runs: [],
                ai_results: [],
              },
            ],
            meta: {
              request_id: "req_runs",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
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
            meta: {
              request_id: "req_project",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const runs = await controllerApi.listWorkflowRuns({ limit: 5 });

    expect(runs[0].project_name).toBe("Project One");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://backend.test/api/v1/workflow-runs?limit=5",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://backend.test/api/v1/projects/proj_1",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("loads risk alert detail with source signal and strategies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            id: "alert_1",
            project_id: "proj_1",
            risk_signal_id: "signal_1",
            status: "open",
            severity: 80,
            title: "Alert one",
            summary: "Needs attention",
            assigned_to_user_id: "user_pm_1",
            detected_by_workflow_run_id: "run_1",
            next_review_at: null,
            resolved_at: null,
            risk_signal: {
              id: "signal_1",
              project_id: "proj_1",
              source_kind: "workflow",
              signal_type: "annotation_backlog",
              severity: 80,
              status: "active",
              title: "Signal one",
              description: null,
              signal_payload: {},
              observed_at: "2026-03-18T08:00:00Z",
              created_by_user_id: "user_pm_1",
            },
            strategies: [
              {
                id: "strategy_1",
                risk_alert_id: "alert_1",
                project_id: "proj_1",
                source_ai_result_id: null,
                status: "proposed",
                proposal_order: 1,
                title: "Strategy one",
                summary: "First proposal",
                strategy_payload: {},
                approved_by_user_id: null,
                approved_at: null,
                applied_at: null,
              },
            ],
          },
          meta: {
            request_id: "req_detail",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const alert = await controllerApi.getRiskAlertDetail("alert_1");

    expect(alert.id).toBe("alert_1");
    expect(alert.risk_signal?.id).toBe("signal_1");
    expect(alert.strategies).toHaveLength(1);
  });

  it("attaches related risk alerts to workflow run detail", async () => {
    const fetchMock = vi.fn();
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              id: "run_1",
              organization_id: "org_1",
              project_id: "proj_1",
              workflow_domain: "risk_monitoring",
              workflow_type: "strategy_generate",
              source_entity_type: "risk_alert",
              source_entity_id: "alert_1",
              status: "waiting_for_human",
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
              started_at: "2026-03-18T08:00:00Z",
              completed_at: null,
              canceled_at: null,
              steps: [],
              coze_runs: [],
              ai_results: [],
            },
            meta: {
              request_id: "req_run",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
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
            meta: {
              request_id: "req_project",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            data: {
              id: "alert_1",
              project_id: "proj_1",
              risk_signal_id: "signal_1",
              status: "open",
              severity: 80,
              title: "Alert one",
              summary: "Needs attention",
              assigned_to_user_id: "user_pm_1",
              detected_by_workflow_run_id: "run_1",
              next_review_at: null,
              resolved_at: null,
              risk_signal: null,
              strategies: [],
            },
            meta: {
              request_id: "req_alert",
              next_cursor: null,
              has_more: false,
            },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const detail = await controllerApi.getWorkflowRunDetail("run_1");

    expect(detail.relatedAlert?.id).toBe("alert_1");
    expect(detail.relatedAlert?.risk_signal_id).toBe("signal_1");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("submits risk strategy generation with idempotency metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            risk_strategies: [{ id: "strategy_1" }],
          },
          meta: {
            request_id: "req_generate",
            next_cursor: null,
            has_more: false,
          },
        }),
        { status: 202, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const controllerApi = await import("./controller-api");
    const result = await controllerApi.requestRiskStrategyGeneration("alert_1");

    expect(result.workflow_run.id).toBe("run_1");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/risk-alerts/alert_1/strategy-generate",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toContain(
      "alert_1",
    );
  });

  it("submits risk strategy approval with idempotency metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            risk_strategies: [],
          },
          meta: {
            request_id: "req_approve",
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

    const controllerApi = await import("./controller-api");
    await controllerApi.requestRiskStrategyDecision("strategy_1", "approve");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/risk-strategies/strategy_1/approve",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "risk-strategy-approve-strategy_1-uuid-fixed",
    );
  });

  it("submits risk strategy rejection with idempotency metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            risk_strategies: [],
          },
          meta: {
            request_id: "req_reject",
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

    const controllerApi = await import("./controller-api");
    await controllerApi.requestRiskStrategyDecision("strategy_2", "reject");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend.test/api/v1/risk-strategies/strategy_2/reject",
      expect.objectContaining({
        method: "POST",
        cache: "no-store",
      }),
    );

    const requestInit = fetchMock.mock.calls[0][1];
    expect(requestInit?.headers).toBeInstanceOf(Headers);
    expect((requestInit?.headers as Headers).get("Idempotency-Key")).toBe(
      "risk-strategy-reject-strategy_2-uuid-fixed",
    );
  });
});
