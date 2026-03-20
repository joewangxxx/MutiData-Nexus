export type ApiMeta = {
  request_id: string;
  next_cursor: string | null;
  has_more: boolean;
};

export type ApiSuccessResponse<T> = {
  data: T;
  meta: ApiMeta;
};

export type ProjectMembership = {
  project_id: string;
  project_code: string;
  project_name: string;
  project_role: string;
  status: string;
};

export type UserSummary = {
  id: string;
  email: string;
  display_name: string;
  status: string;
};

export type ProjectMembershipDetail = {
  id: string;
  project_id: string;
  user_id: string;
  user: UserSummary;
  project_role: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ProjectMembershipMutationResult = {
  membership?: ProjectMembershipDetail;
};

export type MeResponse = {
  user: {
    id: string;
    email: string;
    display_name: string;
    status: string;
  };
  organization: {
    id: string;
    slug: string;
    name: string;
    status: string;
  };
  organization_role: string;
  project_memberships: ProjectMembership[];
  effective_permissions: string[];
};

export type ProjectSummary = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  description: string | null;
  status: string;
  owner_user_id: string;
  settings: Record<string, unknown>;
  counts: Record<string, number>;
};

export type Dataset = {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  source_kind: string;
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type DashboardSummary = {
  project: ProjectSummary;
  queues: Record<string, number>;
  workload: Record<string, number>;
  inbox: Record<string, number>;
  recent_activity: Array<AuditEvent | AiResult>;
};

export type SourceAsset = {
  id: string;
  project_id: string;
  dataset_id: string | null;
  asset_kind: "image" | "audio" | "video";
  uri: string;
  storage_key: string;
  mime_type: string;
  checksum: string;
  duration_ms: number | null;
  width_px: number | null;
  height_px: number | null;
  frame_rate: number | null;
  transcript: string | null;
  metadata: Record<string, unknown>;
};

export type SourceAssetAccess = {
  asset_id: string;
  project_id: string;
  dataset_id: string | null;
  asset_kind: "image" | "audio" | "video";
  delivery_type: string;
  uri: string;
  mime_type: string | null;
};

export type AnnotationTask = {
  id: string;
  project_id: string;
  dataset_id: string;
  source_asset_id: string;
  task_type: string;
  status: string;
  priority: number;
  assigned_to_user_id: string | null;
  reviewer_user_id: string | null;
  created_by_user_id: string;
  current_workflow_run_id: string | null;
  latest_ai_result_id: string | null;
  annotation_schema: Record<string, unknown>;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  claimed_at: string | null;
  due_at: string | null;
  submitted_at: string | null;
  reviewed_at: string | null;
  completed_at: string | null;
};

export type AnnotationRevision = {
  id: string;
  annotation_task_id: string;
  revision_no: number;
  revision_kind: string;
  source_ai_result_id: string | null;
  created_by_user_id: string;
  labels: string[];
  content: Record<string, unknown>;
  review_notes: string | null;
  confidence_score: number | null;
  created_at: string;
};

export type AnnotationReview = {
  id: string;
  annotation_task_id: string;
  revision_id: string;
  reviewed_by_user_id: string;
  decision: "approve" | "reject" | "revise" | string;
  notes: string | null;
  created_at: string;
};

export type RiskSignal = {
  id: string;
  project_id: string;
  source_kind: string;
  signal_type: string;
  severity: number;
  status: string;
  title: string;
  description: string | null;
  signal_payload: Record<string, unknown>;
  observed_at: string;
  created_by_user_id: string;
};

export type RiskAlert = {
  id: string;
  project_id: string;
  risk_signal_id: string;
  status: string;
  severity: number;
  title: string;
  summary: string;
  assigned_to_user_id: string | null;
  detected_by_workflow_run_id: string | null;
  next_review_at: string | null;
  resolved_at: string | null;
};

export type RiskAlertMutationResult = {
  risk_alert?: RiskAlert;
  workflow_run?: WorkflowRun;
};

export type DatasetMutationResult = {
  dataset?: Dataset;
};

export type SourceAssetMutationResult = {
  source_asset?: SourceAsset;
  dataset?: Dataset;
};

export type RiskStrategy = {
  id: string;
  risk_alert_id: string;
  project_id: string;
  source_ai_result_id: string | null;
  status: string;
  proposal_order: number;
  title: string;
  summary: string;
  strategy_payload: Record<string, unknown>;
  approved_by_user_id: string | null;
  approved_at: string | null;
  applied_at: string | null;
};

export type WorkflowStep = {
  id: string;
  workflow_run_id: string;
  step_key: string;
  sequence_no: number;
  status: string;
  attempt_count: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  last_error_code: string | null;
  last_error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type CozeRun = {
  id: string;
  workflow_run_id: string;
  step_id: string;
  coze_workflow_key: string;
  status: string;
  idempotency_key: string;
  external_run_id: string | null;
  attempt_no: number;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  callback_payload: Record<string, unknown>;
  http_status: number | null;
  dispatched_at: string | null;
  acknowledged_at: string | null;
  completed_at: string | null;
  last_polled_at: string | null;
};

export type AiResult = {
  id: string;
  workflow_run_id: string;
  coze_run_id: string | null;
  result_type: string;
  status: string;
  source_entity_type: string;
  source_entity_id: string;
  raw_payload: Record<string, unknown>;
  normalized_payload: Record<string, unknown>;
  reviewed_by_user_id: string | null;
  review_notes: string | null;
  reviewed_at: string | null;
  applied_by_user_id: string | null;
  applied_at: string | null;
};

export type WorkflowRun = {
  id: string;
  organization_id: string;
  project_id: string;
  workflow_domain: string;
  workflow_type: string;
  source_entity_type: string;
  source_entity_id: string;
  status: string;
  priority: number;
  requested_by_user_id: string;
  source: string;
  correlation_key: string;
  idempotency_key: string;
  retry_of_run_id: string | null;
  input_snapshot: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  canceled_at: string | null;
  steps: WorkflowStep[];
  coze_runs: CozeRun[];
  ai_results: AiResult[];
};

export type AuditEvent = {
  id: string;
  organization_id: string;
  project_id: string;
  actor_user_id: string;
  action: string;
  reason_code: string | null;
  entity_type: string;
  entity_id: string;
  workflow_run_id: string | null;
  coze_run_id: string | null;
  request_id: string;
  before_state: Record<string, unknown>;
  after_state: Record<string, unknown>;
  metadata: Record<string, unknown>;
  occurred_at: string;
};
