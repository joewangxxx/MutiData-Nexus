import { cookies, headers } from "next/headers";

import type {
  AiResult,
  AnnotationRevision,
  AnnotationReview,
  AnnotationTask,
  ApiSuccessResponse,
  Dataset,
  DatasetMutationResult,
  DashboardSummary,
  CozeRun,
  ProjectSummary,
  ProjectMembershipDetail,
  ProjectMembershipMutationResult,
  RiskAlert,
  RiskAlertMutationResult,
  RiskSignal,
  RiskStrategy,
  SourceAsset,
  SourceAssetAccess,
  SourceAssetMutationResult,
  UserSummary,
  WorkflowRun,
} from "@/lib/contracts";

const DEFAULT_CONTROLLER_API_URL = "http://127.0.0.1:8000";

export type ControllerApiErrorShape = {
  error: {
    code: string;
    message: string;
    details: unknown[];
  };
};

export class ControllerApiError extends Error {
  status: number;

  code: string;

  details: unknown[];

  constructor(status: number, code: string, message: string, details: unknown[] = []) {
    super(message);
    this.name = "ControllerApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function isControllerApiError(error: unknown): error is ControllerApiError {
  return error instanceof ControllerApiError;
}

export function serializeControllerApiError(error: unknown): ControllerApiErrorShape | null {
  if (!isControllerApiError(error)) {
    return null;
  }

  return {
    error: {
      code: error.code,
      message: error.message,
      details: error.details,
    },
  };
}

type RequestContext = {
  requestHeaders?: HeadersInit;
  idempotencyKey?: string;
};

type ControllerMutationResult = {
  workflow_run?: WorkflowRun;
  coze_run?: CozeRun;
  ai_result?: AiResult | null;
  risk_strategies?: RiskStrategy[];
};

type RiskSignalMutationResult = {
  risk_signal?: RiskSignal;
};

type ProjectRiskGenerationResult = ControllerMutationResult & RiskSignalMutationResult;

type AnnotationReviewMutationResult = {
  review?: AnnotationReview;
  task?: AnnotationTask;
};

type ProjectMembersMutationResult = ProjectMembershipMutationResult;

type AnnotationTaskMutationResult = {
  task?: AnnotationTask;
  workflow_run?: WorkflowRun;
  coze_run?: CozeRun;
  ai_result?: AiResult | null;
};

export type AnnotationQueueTask = AnnotationTask & {
  source_asset: SourceAsset | null;
};

export type ProjectAnnotationQueue = {
  project: ProjectSummary;
  tasks: AnnotationQueueTask[];
};

export type ProjectRiskOverview = {
  project: ProjectSummary;
  alerts: RiskAlert[];
  signals: RiskSignal[];
};

export type RiskAlertDetail = RiskAlert & {
  risk_signal: RiskSignal | null;
  strategies: RiskStrategy[];
};

export type AnnotationWorkbench = {
  project: ProjectSummary;
  task: AnnotationTask;
  sourceAsset: SourceAsset;
  revisions: AnnotationRevision[];
  reviews: AnnotationReview[];
  aiSuggestions: AiResult[];
  linkedRun: WorkflowRun | null;
};

export type WorkflowRunDetail = {
  project: ProjectSummary;
  run: WorkflowRun;
  relatedTask: AnnotationTask | null;
  relatedAlert: RiskAlertDetail | null;
};

function getControllerBaseUrl(): string {
  return (
    process.env.CONTROLLER_API_URL ??
    process.env.NEXT_PUBLIC_CONTROLLER_API_URL ??
    DEFAULT_CONTROLLER_API_URL
  );
}

function joinControllerPath(path: string): string {
  return path.startsWith("/api/v1") ? path : `/api/v1${path.startsWith("/") ? path : `/${path}`}`;
}

function buildControllerUrl(path: string): string {
  const baseUrl = getControllerBaseUrl().replace(/\/+$/, "");
  return new URL(joinControllerPath(path), `${baseUrl}/`).toString();
}

function getControllerAuthHeaderValue(): string | null {
  const token = process.env.CONTROLLER_API_AUTH_TOKEN?.trim();
  if (!token) {
    return null;
  }

  return /^Bearer\s+/i.test(token) ? token : `Bearer ${token}`;
}

async function safeRequestHeaders(requestHeaders?: HeadersInit): Promise<Headers> {
  const merged = new Headers(requestHeaders);

  try {
    if (!merged.has("authorization")) {
      const requestHeadersObject = await headers();
      const authorization = requestHeadersObject.get("authorization");
      if (authorization) {
        merged.set("authorization", authorization);
      }
    }
  } catch {
    // No request context during isolated tests or non-request code paths.
  }

  if (!merged.has("authorization")) {
    const fallbackAuthorization = getControllerAuthHeaderValue();
    if (fallbackAuthorization) {
      merged.set("authorization", fallbackAuthorization);
    }
  }

  try {
    if (!merged.has("cookie")) {
      const cookieStore = await cookies();
      const cookie = cookieStore.toString();
      if (cookie) {
        merged.set("cookie", cookie);
      }
    }
  } catch {
    // Same as above.
  }

  try {
    if (!merged.has("x-request-id")) {
      const requestHeadersObject = await headers();
      const requestId = requestHeadersObject.get("x-request-id");
      if (requestId) {
        merged.set("x-request-id", requestId);
      }
    }
  } catch {
    // Same as above.
  }

  return merged;
}

function createIdempotencyKey(prefix: string): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`;
  return `${prefix}-${randomId}`;
}

async function readJsonPayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function unwrapData<T>(payload: unknown): T {
  if (
    payload &&
    typeof payload === "object" &&
    "data" in payload &&
    (payload as ApiSuccessResponse<T>).data !== undefined
  ) {
    return (payload as ApiSuccessResponse<T>).data;
  }

  return payload as T;
}

function normalizeProjectDetail(data: unknown): ProjectSummary {
  if (data && typeof data === "object" && "project" in data) {
    return (data as { project: ProjectSummary }).project;
  }

  return data as ProjectSummary;
}

function normalizeUserSummary(data: unknown): UserSummary {
  if (data && typeof data === "object" && "user" in data) {
    return normalizeUserSummary((data as { user: UserSummary }).user);
  }

  return data as UserSummary;
}

function normalizeProjectMembership(data: unknown): ProjectMembershipDetail {
  if (data && typeof data === "object" && "membership" in data) {
    return normalizeProjectMembership((data as { membership: ProjectMembershipDetail }).membership);
  }

  return {
    ...(data as ProjectMembershipDetail),
    user: normalizeUserSummary((data as ProjectMembershipDetail).user),
  };
}

function normalizeProjectMembershipList(data: unknown): ProjectMembershipDetail[] {
  if (!Array.isArray(data)) {
    return [];
  }

  return data.map((item) => normalizeProjectMembership(item));
}

function normalizeProjectMembershipMutationResult(data: unknown): ProjectMembersMutationResult {
  if (data && typeof data === "object" && "membership" in data) {
    return {
      membership: normalizeProjectMembership((data as { membership: ProjectMembershipDetail }).membership),
    };
  }

  if (data && typeof data === "object" && "project_id" in data && "user_id" in data) {
    return {
      membership: normalizeProjectMembership(data),
    };
  }

  return data as ProjectMembersMutationResult;
}

function normalizeTaskDetail(data: unknown): AnnotationTask {
  if (data && typeof data === "object" && "task" in data) {
    return (data as { task: AnnotationTask }).task;
  }

  return data as AnnotationTask;
}

function normalizeSourceAsset(data: unknown): SourceAsset {
  if (data && typeof data === "object" && "source_asset" in data) {
    return (data as { source_asset: SourceAsset }).source_asset;
  }

  return data as SourceAsset;
}

function normalizeRiskSignal(data: unknown): RiskSignal {
  if (data && typeof data === "object" && "risk_signal" in data) {
    return (data as { risk_signal: RiskSignal }).risk_signal;
  }

  return data as RiskSignal;
}

function normalizeDatasetMutationResult(data: unknown): DatasetMutationResult {
  if (data && typeof data === "object" && "dataset" in data) {
    return {
      dataset: normalizeDataset((data as { dataset: Dataset }).dataset),
    };
  }

  if (data && typeof data === "object" && "project_id" in data && "source_kind" in data) {
    return {
      dataset: normalizeDataset(data),
    };
  }

  return data as DatasetMutationResult;
}

function normalizeSourceAssetMutationResult(data: unknown): SourceAssetMutationResult {
  if (data && typeof data === "object" && "source_asset" in data) {
    const payload = data as { source_asset: SourceAsset; dataset?: Dataset };
    return {
      source_asset: normalizeSourceAsset(payload.source_asset),
      dataset: payload.dataset ? normalizeDataset(payload.dataset) : undefined,
    };
  }

  if (data && typeof data === "object" && "project_id" in data && "asset_kind" in data) {
    return {
      source_asset: normalizeSourceAsset(data),
    };
  }

  return data as SourceAssetMutationResult;
}

function normalizeSourceAssetAccess(data: unknown): SourceAssetAccess {
  if (data && typeof data === "object" && "access" in data) {
    return (data as { access: SourceAssetAccess }).access;
  }

  return data as SourceAssetAccess;
}

function normalizeDataset(data: unknown): Dataset {
  if (data && typeof data === "object" && "dataset" in data) {
    return (data as { dataset: Dataset }).dataset;
  }

  return data as Dataset;
}

async function controllerRequest<T>(
  path: string,
  {
    method = "GET",
    body,
    requestHeaders,
    idempotencyKey,
  }: {
    method?: string;
    body?: unknown;
    requestHeaders?: HeadersInit;
    idempotencyKey?: string;
  } = {},
): Promise<T> {
  const headers = await safeRequestHeaders(requestHeaders);
  headers.set("accept", "application/json");
  if (body !== undefined) {
    headers.set("content-type", "application/json");
  }
  if (idempotencyKey) {
    headers.set("Idempotency-Key", idempotencyKey);
  }

  const response = await fetch(buildControllerUrl(path), {
    method,
    cache: "no-store",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const payload = await readJsonPayload(response);

  if (!response.ok) {
    if (
      payload &&
      typeof payload === "object" &&
      "error" in payload &&
      (payload as ControllerApiErrorShape).error
    ) {
      const apiError = (payload as ControllerApiErrorShape).error;
      throw new ControllerApiError(
        response.status,
        apiError.code,
        apiError.message,
        Array.isArray(apiError.details) ? apiError.details : [],
      );
    }

    throw new ControllerApiError(
      response.status,
      "http_error",
      `Request to ${path} failed with status ${response.status}.`,
      [],
    );
  }

  return unwrapData<T>(payload);
}

function normalizeStatusList(tasks: AnnotationTask[]): AnnotationTask[] {
  return [...tasks].sort((left, right) => right.priority - left.priority);
}

function normalizeRiskAlertList(alerts: RiskAlert[]): RiskAlert[] {
  return [...alerts].sort((left, right) => right.severity - left.severity);
}

function normalizeRiskSignalList(signals: RiskSignal[]): RiskSignal[] {
  return [...signals]
    .map((signal) => normalizeRiskSignal(signal))
    .sort((left, right) => right.severity - left.severity);
}

function normalizeRiskStrategyList(strategies: RiskStrategy[]): RiskStrategy[] {
  return [...strategies].sort((left, right) => left.proposal_order - right.proposal_order);
}

function normalizeAnnotationReviewList(reviews: AnnotationReview[]): AnnotationReview[] {
  return [...reviews].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

export async function getProject(projectId: string): Promise<ProjectSummary> {
  const data = await controllerRequest<unknown>(`/projects/${projectId}`);
  return normalizeProjectDetail(data);
}

export async function listProjectMembers(
  projectId: string,
  context: RequestContext = {},
): Promise<ProjectMembershipDetail[]> {
  const data = await controllerRequest<unknown>(`/projects/${projectId}/members`, {
    requestHeaders: context.requestHeaders,
  });
  return normalizeProjectMembershipList(data);
}

export async function getProjectMembers(
  projectId: string,
  context: RequestContext = {},
): Promise<ProjectMembershipDetail[]> {
  return listProjectMembers(projectId, context);
}

export async function updateProjectMember(
  projectId: string,
  membershipId: string,
  body: {
    project_role?: string;
    status?: string;
  },
  context: RequestContext = {},
): Promise<ProjectMembersMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`project-member-update-${membershipId}`);
  const data = await controllerRequest<unknown>(`/projects/${projectId}/members/${membershipId}`, {
    method: "PATCH",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeProjectMembershipMutationResult(data);
}

export async function deleteProjectMember(
  projectId: string,
  membershipId: string,
  context: RequestContext = {},
): Promise<ProjectMembersMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`project-member-delete-${membershipId}`);
  const data = await controllerRequest<unknown>(`/projects/${projectId}/members/${membershipId}`, {
    method: "DELETE",
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeProjectMembershipMutationResult(data);
}

export async function getProjectDashboard(projectId: string): Promise<DashboardSummary> {
  const data = await controllerRequest<unknown>(`/projects/${projectId}/dashboard`);
  return data as DashboardSummary;
}

export async function listProjectDatasets(
  projectId: string,
  filters: {
    limit?: number;
  } = {},
): Promise<Dataset[]> {
  const params = new URLSearchParams();

  params.set("limit", String(filters.limit ?? 50));

  const query = params.toString();
  const data = await controllerRequest<unknown>(
    `/projects/${projectId}/datasets${query ? `?${query}` : ""}`,
  );
  return Array.isArray(data) ? data.map((dataset) => normalizeDataset(dataset)) : [];
}

export async function listProjectSourceAssets(
  projectId: string,
  filters: {
    datasetId?: string;
    assetKind?: SourceAsset["asset_kind"];
    limit?: number;
  } = {},
): Promise<SourceAsset[]> {
  const params = new URLSearchParams();

  if (filters.datasetId) {
    params.set("dataset_id", filters.datasetId);
  }
  if (filters.assetKind) {
    params.set("asset_kind", filters.assetKind);
  }
  params.set("limit", String(filters.limit ?? 50));

  const query = params.toString();
  const data = await controllerRequest<unknown>(
    `/projects/${projectId}/source-assets${query ? `?${query}` : ""}`,
  );
  return Array.isArray(data) ? data.map((asset) => normalizeSourceAsset(asset)) : [];
}

export async function createProjectDataset(
  projectId: string,
  body: {
    name: string;
    source_kind: string;
    description?: string;
    metadata?: Record<string, unknown>;
  },
  context: RequestContext = {},
): Promise<DatasetMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`dataset-create-${projectId}`);
  const data = await controllerRequest<unknown>(`/projects/${projectId}/datasets`, {
    method: "POST",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeDatasetMutationResult(data);
}

export async function updateDataset(
  datasetId: string,
  body: {
    name?: string;
    source_kind?: string;
    description?: string;
    metadata?: Record<string, unknown>;
  },
  context: RequestContext = {},
): Promise<DatasetMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`dataset-update-${datasetId}`);
  const data = await controllerRequest<unknown>(`/datasets/${datasetId}`, {
    method: "PATCH",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeDatasetMutationResult(data);
}

export async function registerProjectSourceAsset(
  projectId: string,
  body: {
    asset_kind: SourceAsset["asset_kind"];
    uri: string;
    dataset_id?: string;
    storage_key?: string;
    mime_type?: string;
    checksum?: string;
    duration_ms?: number;
    width_px?: number;
    height_px?: number;
    frame_rate?: number;
    transcript?: string;
    metadata?: Record<string, unknown>;
  },
  context: RequestContext = {},
): Promise<SourceAssetMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`source-asset-create-${projectId}`);
  const data = await controllerRequest<unknown>(`/projects/${projectId}/source-assets`, {
    method: "POST",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeSourceAssetMutationResult(data);
}

export async function updateSourceAsset(
  assetId: string,
  body: {
    dataset_id?: string;
    storage_key?: string;
    mime_type?: string;
    checksum?: string;
    duration_ms?: number;
    width_px?: number;
    height_px?: number;
    frame_rate?: number;
    transcript?: string;
    metadata?: Record<string, unknown>;
  },
  context: RequestContext = {},
): Promise<SourceAssetMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`source-asset-update-${assetId}`);
  const data = await controllerRequest<unknown>(`/source-assets/${assetId}`, {
    method: "PATCH",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeSourceAssetMutationResult(data);
}

export async function listAnnotationTasks(
  projectId: string,
): Promise<AnnotationTask[]> {
  const data = await controllerRequest<unknown>(
    `/projects/${projectId}/annotation-tasks?limit=20`,
  );
  const tasks = Array.isArray(data) ? data : [];
  return normalizeStatusList(tasks as AnnotationTask[]);
}

export async function createAnnotationTask(
  projectId: string,
  body: {
    source_asset_id?: string;
    dataset_id?: string;
    task_type: string;
    priority?: number;
    assigned_to_user_id?: string;
    reviewer_user_id?: string;
    annotation_schema?: Record<string, unknown>;
    input_payload?: Record<string, unknown>;
  },
  context: RequestContext = {},
): Promise<AnnotationTaskMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`annotation-create-${projectId}`);
  return controllerRequest<AnnotationTaskMutationResult>(
    `/projects/${projectId}/annotation-tasks`,
    {
      method: "POST",
      body,
      requestHeaders: context.requestHeaders,
      idempotencyKey,
    },
  );
}

export async function getAnnotationTask(taskId: string): Promise<AnnotationTask> {
  const data = await controllerRequest<unknown>(`/annotation-tasks/${taskId}`);
  return normalizeTaskDetail(data);
}

export async function updateAnnotationTask(
  taskId: string,
  body: {
    assigned_to_user_id?: string;
    reviewer_user_id?: string;
    priority?: number;
    due_at?: string | null;
    status?: string;
  },
  context: RequestContext = {},
): Promise<AnnotationTaskMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`annotation-update-${taskId}`);
  return controllerRequest<AnnotationTaskMutationResult>(`/annotation-tasks/${taskId}`, {
    method: "PATCH",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });
}

export async function claimAnnotationTask(
  taskId: string,
  context: RequestContext = {},
): Promise<AnnotationTaskMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`annotation-claim-${taskId}`);
  return controllerRequest<AnnotationTaskMutationResult>(`/annotation-tasks/${taskId}/claim`, {
    method: "POST",
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });
}

export async function getAnnotationTaskRevisions(
  taskId: string,
): Promise<AnnotationRevision[]> {
  const data = await controllerRequest<unknown>(`/annotation-tasks/${taskId}/revisions`);
  return Array.isArray(data) ? (data as AnnotationRevision[]) : [];
}

export async function getAnnotationTaskReviews(taskId: string): Promise<AnnotationReview[]> {
  const data = await controllerRequest<unknown>(`/annotation-tasks/${taskId}/reviews`);
  return Array.isArray(data) ? normalizeAnnotationReviewList(data as AnnotationReview[]) : [];
}

export async function getAnnotationTaskAiResults(taskId: string): Promise<AiResult[]> {
  const data = await controllerRequest<unknown>(`/annotation-tasks/${taskId}/ai-results`);
  return Array.isArray(data) ? (data as AiResult[]) : [];
}

export async function getSourceAsset(assetId: string): Promise<SourceAsset> {
  const data = await controllerRequest<unknown>(`/source-assets/${assetId}`);
  return normalizeSourceAsset(data);
}

export async function getSourceAssetAccess(assetId: string): Promise<SourceAssetAccess> {
  const data = await controllerRequest<unknown>(`/source-assets/${assetId}/access`, {
    method: "POST",
  });
  return normalizeSourceAssetAccess(data);
}

export async function getWorkflowRun(runId: string): Promise<WorkflowRun> {
  const data = await controllerRequest<unknown>(`/workflow-runs/${runId}`);
  return data as WorkflowRun;
}

export async function listWorkflowRuns(filters: {
  projectId?: string;
  workflowDomain?: string;
  status?: string;
  sourceEntityType?: string;
  sourceEntityId?: string;
  limit?: number;
} = {}): Promise<Array<WorkflowRun & { project_name: string }>> {
  const params = new URLSearchParams();

  if (filters.projectId) {
    params.set("project_id", filters.projectId);
  }
  if (filters.workflowDomain) {
    params.set("workflow_domain", filters.workflowDomain);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.sourceEntityType) {
    params.set("source_entity_type", filters.sourceEntityType);
  }
  if (filters.sourceEntityId) {
    params.set("source_entity_id", filters.sourceEntityId);
  }
  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }

  const query = params.toString();
  const data = await controllerRequest<unknown>(`/workflow-runs${query ? `?${query}` : ""}`);
  const runs = Array.isArray(data) ? (data as WorkflowRun[]) : [];
  const projectNames = new Map<string, string>();
  const uniqueProjectIds = [...new Set(runs.map((run) => run.project_id))];

  await Promise.all(
    uniqueProjectIds.map(async (projectId) => {
      try {
        const project = await getProject(projectId);
        projectNames.set(projectId, project.name);
      } catch {
        projectNames.set(projectId, projectId);
      }
    }),
  );

  return runs.map((run) => ({
    ...run,
    project_name: projectNames.get(run.project_id) ?? run.project_id,
  }));
}

export async function listRiskSignals(projectId: string): Promise<RiskSignal[]> {
  const data = await controllerRequest<unknown>(`/projects/${projectId}/risk-signals`);
  const signals = Array.isArray(data) ? (data as RiskSignal[]) : [];
  return normalizeRiskSignalList(signals);
}

function normalizeRiskSignalMutationResult(data: unknown): RiskSignalMutationResult {
  if (data && typeof data === "object" && "risk_signal" in data) {
    return {
      risk_signal: normalizeRiskSignal((data as { risk_signal: RiskSignal }).risk_signal),
    };
  }

  if (data && typeof data === "object" && "project_id" in data && "source_kind" in data) {
    return {
      risk_signal: normalizeRiskSignal(data),
    };
  }

  return data as RiskSignalMutationResult;
}

export async function createProjectRiskSignal(
  projectId: string,
  body: {
    source_kind: string;
    signal_type: string;
    severity: number;
    title: string;
    observed_at: string;
    description?: string;
    signal_payload?: Record<string, unknown>;
    created_by_user_id?: string;
  },
  context: RequestContext = {},
): Promise<RiskSignalMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`risk-signal-create-${projectId}`);
  const data = await controllerRequest<unknown>(`/projects/${projectId}/risk-signals`, {
    method: "POST",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });

  return normalizeRiskSignalMutationResult(data);
}

export async function requestProjectRiskGeneration(
  projectId: string,
  body: {
    source_kind: string;
    signal_type: string;
    severity: number;
    title: string;
    observed_at: string;
    description?: string;
    signal_payload?: Record<string, unknown>;
    context_overrides?: Record<string, unknown>;
  },
  context: RequestContext = {},
): Promise<ProjectRiskGenerationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`risk-generate-${projectId}`);
  return controllerRequest<ProjectRiskGenerationResult>(`/projects/${projectId}/risk-generate`, {
    method: "POST",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });
}

export async function listRiskAlerts(projectId: string): Promise<RiskAlert[]> {
  const data = await controllerRequest<unknown>(`/projects/${projectId}/risk-alerts`);
  const alerts = Array.isArray(data) ? (data as RiskAlert[]) : [];
  return normalizeRiskAlertList(alerts);
}

export async function getRiskAlertDetail(alertId: string): Promise<RiskAlertDetail> {
  const data = await controllerRequest<unknown>(`/risk-alerts/${alertId}`);

  if (!data || typeof data !== "object") {
    return {
      ...(data as RiskAlert),
      risk_signal: null,
      strategies: [],
    };
  }

  const payload = data as Partial<RiskAlertDetail> & {
    risk_signal?: RiskSignal | null;
    source_signal?: RiskSignal | null;
    strategies?: RiskStrategy[];
  };

  return {
    ...(payload as RiskAlert),
    risk_signal: payload.risk_signal ?? payload.source_signal ?? null,
    strategies: normalizeRiskStrategyList(payload.strategies ?? []),
  };
}

export async function patchRiskAlert(
  alertId: string,
  body: {
    status?: string;
    assigned_to_user_id?: string | null;
    title?: string;
    summary?: string | null;
    severity?: number;
    next_review_at?: string | null;
  },
  context: RequestContext = {},
): Promise<RiskAlertMutationResult> {
  const idempotencyKey = context.idempotencyKey ?? createIdempotencyKey(`risk-alert-patch-${alertId}`);
  return controllerRequest<RiskAlertMutationResult>(`/risk-alerts/${alertId}`, {
    method: "PATCH",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });
}

export async function acknowledgeRiskAlert(
  alertId: string,
  context: RequestContext = {},
): Promise<RiskAlertMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`risk-alert-acknowledge-${alertId}`);
  return controllerRequest<RiskAlertMutationResult>(`/risk-alerts/${alertId}/acknowledge`, {
    method: "POST",
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });
}

export async function getProjectRiskOverview(
  projectId: string,
): Promise<ProjectRiskOverview> {
  const [project, alerts, signals] = await Promise.all([
    getProject(projectId),
    listRiskAlerts(projectId),
    listRiskSignals(projectId),
  ]);

  return {
    project,
    alerts,
    signals,
  };
}

export async function getProjectAnnotationQueue(
  projectId: string,
): Promise<ProjectAnnotationQueue> {
  const [project, tasks] = await Promise.all([getProject(projectId), listAnnotationTasks(projectId)]);
  const queueTasks = tasks.filter((task) =>
    ["queued", "claimed", "in_progress", "submitted"].includes(task.status),
  );
  const sourceAssets = await Promise.all(
    queueTasks.map(async (task) => {
      try {
        return await getSourceAsset(task.source_asset_id);
      } catch {
        return null;
      }
    }),
  );

  return {
    project,
    tasks: queueTasks.map((task, index) => ({
      ...task,
      source_asset: sourceAssets[index],
    })),
  };
}

export async function getAnnotationWorkbench(
  projectId: string,
  taskId: string,
): Promise<AnnotationWorkbench> {
  const [project, task] = await Promise.all([getProject(projectId), getAnnotationTask(taskId)]);

  if (task.project_id !== project.id) {
    throw new ControllerApiError(404, "not_found", "Annotation task not found.", []);
  }

  const [sourceAsset, revisions, reviews, aiSuggestions, linkedRun] = await Promise.all([
    getSourceAsset(task.source_asset_id),
    getAnnotationTaskRevisions(taskId),
    getAnnotationTaskReviews(taskId),
    getAnnotationTaskAiResults(taskId),
    task.current_workflow_run_id
      ? getWorkflowRun(task.current_workflow_run_id).catch((error) => {
          if (isControllerApiError(error) && error.status === 404) {
            return null;
          }

          throw error;
        })
      : Promise.resolve(null),
  ]);

  return {
    project,
    task,
    sourceAsset,
    revisions,
    reviews,
    aiSuggestions,
    linkedRun,
  };
}

export async function getWorkflowRunDetail(
  runId: string,
): Promise<WorkflowRunDetail> {
  const run = await getWorkflowRun(runId);
  const project = await getProject(run.project_id);
  const relatedTask =
    run.source_entity_type === "annotation_task"
      ? await getAnnotationTask(run.source_entity_id).catch((error) => {
          if (isControllerApiError(error) && error.status === 404) {
            return null;
          }

          throw error;
        })
      : null;
  const relatedAlert =
    run.source_entity_type === "risk_alert"
      ? await getRiskAlertDetail(run.source_entity_id).catch((error) => {
          if (isControllerApiError(error) && error.status === 404) {
            return null;
          }

          throw error;
        })
      : null;

  if (relatedTask && relatedTask.project_id !== project.id) {
    throw new ControllerApiError(404, "not_found", "Annotation task not found.", []);
  }

  if (relatedAlert && relatedAlert.project_id !== project.id) {
    throw new ControllerApiError(404, "not_found", "Risk alert not found.", []);
  }

  return {
    project,
    run,
    relatedTask,
    relatedAlert,
  };
}

export async function requestRiskStrategyGeneration(
  alertId: string,
  body: {
    proposal_count?: number;
    context_overrides?: Record<string, unknown>;
  } = {},
  context: RequestContext = {},
): Promise<ControllerMutationResult> {
  const idempotencyKey = context.idempotencyKey ?? createIdempotencyKey(`risk-strategy-generate-${alertId}`);
  return controllerRequest<ControllerMutationResult>(
    `/risk-alerts/${alertId}/strategy-generate`,
    {
      method: "POST",
      body,
      requestHeaders: context.requestHeaders,
      idempotencyKey,
    },
  );
}

export async function requestRiskStrategyDecision(
  strategyId: string,
  decision: "approve" | "reject",
  body: {
    review_notes?: string;
  } = {},
  context: RequestContext = {},
): Promise<ControllerMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`risk-strategy-${decision}-${strategyId}`);

  return controllerRequest<ControllerMutationResult>(
    `/risk-strategies/${strategyId}/${decision}`,
    {
      method: "POST",
      body,
      requestHeaders: context.requestHeaders,
      idempotencyKey,
    },
  );
}

export async function requestAnnotationGeneration(
  taskId: string,
  body: {
    context_overrides?: Record<string, unknown>;
    force_refresh?: boolean;
  } = {},
  context: RequestContext = {},
): Promise<ControllerMutationResult> {
  const idempotencyKey = context.idempotencyKey ?? createIdempotencyKey(`annotation-generate-${taskId}`);
  return controllerRequest<ControllerMutationResult>(
    `/annotation-tasks/${taskId}/ai-generate`,
    {
      method: "POST",
      body,
      requestHeaders: context.requestHeaders,
      idempotencyKey,
    },
  );
}

export async function requestAnnotationReview(
  taskId: string,
  body: {
    revision_id: string;
    decision: "approve" | "reject" | "revise";
    notes?: string;
  },
  context: RequestContext = {},
): Promise<AnnotationReviewMutationResult> {
  const idempotencyKey =
    context.idempotencyKey ?? createIdempotencyKey(`annotation-review-${taskId}`);
  return controllerRequest<AnnotationReviewMutationResult>(`/annotation-tasks/${taskId}/reviews`, {
    method: "POST",
    body,
    requestHeaders: context.requestHeaders,
    idempotencyKey,
  });
}

export async function submitAnnotationRevision(
  taskId: string,
  body: {
    labels: string[];
    content: Record<string, unknown>;
    review_notes?: string;
    confidence_score?: number;
  },
  context: RequestContext = {},
): Promise<ControllerMutationResult> {
  const idempotencyKey = context.idempotencyKey ?? createIdempotencyKey(`annotation-submission-${taskId}`);
  return controllerRequest<ControllerMutationResult>(
    `/annotation-tasks/${taskId}/submissions`,
    {
      method: "POST",
      body,
      requestHeaders: context.requestHeaders,
      idempotencyKey,
    },
  );
}
