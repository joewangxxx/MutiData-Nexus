import type {
  AiResult,
  AnnotationRevision,
  AnnotationTask,
  AuditEvent,
  DashboardSummary,
  ProjectSummary,
  RiskAlert,
  RiskSignal,
  RiskStrategy,
  SourceAsset,
  WorkflowRun,
} from "@/lib/contracts";
import {
  aiResults,
  annotationRevisions,
  annotationTasks,
  auditEvents,
  dashboardSummaries,
  meResponse,
  projectSummaries,
  riskAlerts,
  riskSignals,
  riskStrategies,
  sourceAssets,
  workflowRuns,
} from "@/lib/mock-data";

export type ShellSnapshot = {
  currentUser: {
    id: string;
    displayName: string;
    organizationName: string;
    organizationRole: string;
  };
  projectMemberships: typeof meResponse.project_memberships;
};

export type InboxItem = {
  id: string;
  kind: "task" | "risk" | "workflow";
  title: string;
  summary: string;
  href: string;
  projectId: string;
  projectName: string;
  status: string;
  priority: number;
};

export type ProjectOverviewModel = {
  project: ProjectSummary;
  dashboard: DashboardSummary;
  tasks: AnnotationTask[];
  alerts: RiskAlert[];
  runs: WorkflowRun[];
};

export type TaskWorkbenchModel = {
  project: ProjectSummary;
  task: AnnotationTask;
  sourceAsset: SourceAsset;
  revisions: AnnotationRevision[];
  aiSuggestions: AiResult[];
  linkedRun: WorkflowRun | null;
};

export type ProjectRiskModel = {
  project: ProjectSummary;
  dashboard: DashboardSummary;
  alerts: RiskAlert[];
  signals: RiskSignal[];
  strategies: RiskStrategy[];
  recentRuns: WorkflowRun[];
};

const userDirectory: Record<string, string> = {
  user_annotator_1: "Lin Chen",
  user_annotator_2: "Owen Park",
  user_reviewer_1: "Mia Patel",
  user_reviewer_2: "Nora Diaz",
  user_pm_1: "Harper Li",
  user_pm_2: "Sofia Kim",
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function getProject(projectId: string): ProjectSummary {
  const project = projectSummaries.find((item) => item.id === projectId);
  if (!project) {
    throw new Error(`Unknown project: ${projectId}`);
  }

  return clone(project);
}

function getDashboard(projectId: string): DashboardSummary {
  const dashboard = dashboardSummaries.find((item) => item.project.id === projectId);
  if (!dashboard) {
    throw new Error(`Unknown dashboard: ${projectId}`);
  }

  return clone(dashboard);
}

function getRun(runId: string): WorkflowRun {
  const run = workflowRuns.find((item) => item.id === runId);
  if (!run) {
    throw new Error(`Unknown workflow run: ${runId}`);
  }

  return {
    ...clone(run),
    ai_results: clone(aiResults.filter((result) => result.workflow_run_id === runId)),
  };
}

function getTask(taskId: string): AnnotationTask {
  const task = annotationTasks.find((item) => item.id === taskId);
  if (!task) {
    throw new Error(`Unknown annotation task: ${taskId}`);
  }

  return clone(task);
}

export async function getShellSnapshot(): Promise<ShellSnapshot> {
  return {
    currentUser: {
      id: meResponse.user.id,
      displayName: meResponse.user.display_name,
      organizationName: meResponse.organization.name,
      organizationRole: meResponse.organization_role,
    },
    projectMemberships: clone(meResponse.project_memberships),
  };
}

export async function getDashboardLanding() {
  const focusProject = projectSummaries[0];
  return {
    shell: await getShellSnapshot(),
    focusProject: clone(focusProject),
    dashboard: getDashboard(focusProject.id),
    projects: clone(projectSummaries),
    inboxItems: await listInboxItems(),
  };
}

export async function listVisibleProjects(): Promise<ProjectSummary[]> {
  return clone(projectSummaries);
}

export async function getProjectOverview(
  projectId: string,
): Promise<ProjectOverviewModel> {
  return {
    project: getProject(projectId),
    dashboard: getDashboard(projectId),
    tasks: clone(annotationTasks.filter((task) => task.project_id === projectId)),
    alerts: clone(riskAlerts.filter((alert) => alert.project_id === projectId)),
    runs: workflowRuns
      .filter((run) => run.project_id === projectId)
      .map((run) => getRun(run.id)),
  };
}

export async function listProjectAnnotationTasks(
  projectId: string,
): Promise<Array<AnnotationTask & { source_asset: SourceAsset | null }>> {
  return annotationTasks
    .filter((task) => task.project_id === projectId)
    .map((task) => ({
      ...clone(task),
      source_asset:
        sourceAssets.find((asset) => asset.id === task.source_asset_id) ?? null,
    }));
}

export async function getTaskWorkbench(
  projectId: string,
  taskId: string,
): Promise<TaskWorkbenchModel> {
  const task = getTask(taskId);
  if (task.project_id !== projectId) {
    throw new Error(`Task ${taskId} does not belong to project ${projectId}`);
  }

  const sourceAsset = sourceAssets.find((asset) => asset.id === task.source_asset_id);
  if (!sourceAsset) {
    throw new Error(`Missing source asset for task ${task.id}`);
  }

  return {
    project: getProject(projectId),
    task,
    sourceAsset: clone(sourceAsset),
    revisions: clone(
      annotationRevisions.filter((revision) => revision.annotation_task_id === taskId),
    ),
    aiSuggestions: clone(
      aiResults.filter((result) => result.source_entity_id === taskId),
    ),
    linkedRun: task.current_workflow_run_id ? getRun(task.current_workflow_run_id) : null,
  };
}

export async function getProjectRisk(projectId: string): Promise<ProjectRiskModel> {
  const alerts = riskAlerts.filter((alert) => alert.project_id === projectId);
  return {
    project: getProject(projectId),
    dashboard: getDashboard(projectId),
    alerts: clone(alerts),
    signals: clone(riskSignals.filter((signal) => signal.project_id === projectId)),
    strategies: clone(
      riskStrategies.filter((strategy) =>
        alerts.some((alert) => alert.id === strategy.risk_alert_id),
      ),
    ),
    recentRuns: workflowRuns
      .filter((run) => run.project_id === projectId && run.workflow_domain === "risk")
      .map((run) => getRun(run.id)),
  };
}

export async function listWorkflowRuns(): Promise<
  Array<WorkflowRun & { project_name: string }>
> {
  return workflowRuns.map((run) => ({
    ...getRun(run.id),
    project_name:
      projectSummaries.find((project) => project.id === run.project_id)?.name ??
      run.project_id,
  }));
}

export async function getWorkflowRunDetail(runId: string) {
  const run = getRun(runId);
  return {
    run,
    project: getProject(run.project_id),
    relatedTask:
      run.source_entity_type === "annotation_task"
        ? clone(
            annotationTasks.find((task) => task.id === run.source_entity_id) ?? null,
          )
        : null,
    relatedAlert:
      run.source_entity_type === "risk_alert"
        ? clone(riskAlerts.find((alert) => alert.id === run.source_entity_id) ?? null)
        : null,
  };
}

export async function listInboxItems(): Promise<InboxItem[]> {
  const items: InboxItem[] = [
    ...annotationTasks
      .filter(
        (task) =>
          task.assigned_to_user_id === meResponse.user.id &&
          ["queued", "in_progress", "submitted"].includes(task.status),
      )
      .map((task) => {
        const project = projectSummaries.find((item) => item.id === task.project_id);
        return {
          id: `inbox-${task.id}`,
          kind: "task" as const,
          title: `Task ${task.id} needs progress`,
          summary: `${task.task_type} is ${task.status.replaceAll("_", " ")} and due soon.`,
          href: `/projects/${task.project_id}/annotation/tasks/${task.id}`,
          projectId: task.project_id,
          projectName: project?.name ?? task.project_id,
          status: task.status,
          priority: task.priority,
        };
      }),
    ...riskAlerts
      .filter((alert) => alert.status !== "resolved")
      .map((alert) => {
        const project = projectSummaries.find((item) => item.id === alert.project_id);
        return {
          id: `inbox-${alert.id}`,
          kind: "risk" as const,
          title: alert.title,
          summary: alert.summary,
          href: `/projects/${alert.project_id}/risk`,
          projectId: alert.project_id,
          projectName: project?.name ?? alert.project_id,
          status: alert.status,
          priority: alert.severity,
        };
      }),
    ...workflowRuns
      .filter((run) => ["waiting_for_human", "failed", "running"].includes(run.status))
      .map((run) => {
        const project = projectSummaries.find((item) => item.id === run.project_id);
        return {
          id: `inbox-${run.id}`,
          kind: "workflow" as const,
          title: `${run.workflow_domain} run ${run.status.replaceAll("_", " ")}`,
          summary:
            run.error_message ??
            `Run is linked to ${run.source_entity_type} ${run.source_entity_id}.`,
          href: `/workflow-runs/${run.id}`,
          projectId: run.project_id,
          projectName: project?.name ?? run.project_id,
          status: run.status,
          priority: run.priority,
        };
      }),
  ];

  return items
    .sort((left, right) => right.priority - left.priority)
    .slice(0, 8);
}

export async function listActivityForProject(
  projectId: string,
): Promise<Array<AuditEvent | AiResult>> {
  return clone(
    [...auditEvents, ...aiResults].filter((item) => {
      if ("project_id" in item) {
        return item.project_id === projectId;
      }

      const sourceTask = annotationTasks.find(
        (task) => task.id === item.source_entity_id && task.project_id === projectId,
      );
      const sourceAlert = riskAlerts.find(
        (alert) => alert.id === item.source_entity_id && alert.project_id === projectId,
      );

      return Boolean(sourceTask ?? sourceAlert);
    }),
  );
}

export function getUserName(userId: string | null): string {
  if (!userId) {
    return "Unassigned";
  }

  return userDirectory[userId] ?? userId;
}
