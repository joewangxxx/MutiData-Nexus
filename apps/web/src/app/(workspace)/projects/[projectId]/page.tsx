import { notFound } from "next/navigation";

import {
  EmptyState,
  MetricCard,
  MetricGrid,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui/primitives";
import {
  getProjectMembers,
  getProjectDashboard,
  isControllerApiError,
  listAnnotationTasks,
  listRiskAlerts,
  listWorkflowRuns,
} from "@/lib/controller-api";
import { describeSeverity, formatCount, formatDateTime, humanizeToken } from "@/lib/presenters";
import { ProjectMemberManagementPanel } from "@/components/projects/project-member-management-panel";

export default async function ProjectOverviewPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [dashboard, tasks, alerts, riskRuns, members] = await Promise.all([
    getProjectDashboard(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    listAnnotationTasks(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    listRiskAlerts(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    listWorkflowRuns({
      projectId,
      workflowDomain: "risk_monitoring",
      limit: 4,
    }).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    getProjectMembers(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
  ]);

  if (!dashboard || !tasks || !alerts || !riskRuns || !members) {
    notFound();
  }

  const activeAlerts = alerts.filter((alert) => !["resolved", "dismissed"].includes(alert.status));
  const escalatedAlerts = activeAlerts.filter((alert) => alert.status === "escalated");

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Project workspace"
        title={dashboard.project.name}
        description={dashboard.project.description ?? "Project overview"}
        actions={
          <div className="button-row">
            <a className="button-secondary" href={`/projects/${projectId}/catalog`}>
              Open catalog
            </a>
            <a className="button-primary" href={`/projects/${projectId}/annotation/queue`}>
              Open annotation queue
            </a>
            <a className="button-secondary" href={`/projects/${projectId}/risk`}>
              Open risk monitor
            </a>
          </div>
        }
      />

      <MetricGrid>
        <MetricCard
          label="Annotation queue"
          value={formatCount(dashboard.queues.annotation)}
          meta="Active and submitted work in this project"
          tone="info"
        />
        <MetricCard
          label="Risk queue"
          value={formatCount(dashboard.queues.risk)}
          meta="Open exception items requiring review"
          tone="warning"
        />
        <MetricCard
          label="Active runs"
          value={formatCount(dashboard.workload.active_runs)}
          meta="Backend executions tied to this workspace"
          tone="success"
        />
        <MetricCard
          label="Failures"
          value={formatCount(dashboard.workload.failures_last_24h)}
          meta="Workflow issues in the last 24 hours"
          tone="danger"
        />
      </MetricGrid>

      <div className="section-grid">
        <div className="span-12">
          <SectionCard
            title="Project members"
            description="Project managers can review live membership records, adjust roles, and deactivate access without leaving the overview."
          >
            <ProjectMemberManagementPanel projectId={projectId} members={members} />
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Workstream snapshot"
            description="Project-scoped navigation lets users move directly from the overview into the active queue or risk board."
          >
            {tasks.length > 0 ? (
              <div className="stack-list">
                {tasks.slice(0, 3).map((task) => (
                  <article key={task.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={task.status} />
                      <span>{humanizeToken(task.task_type)}</span>
                    </div>
                    <h3>{task.id}</h3>
                    <p className="muted-text">
                      Assigned to {task.assigned_to_user_id ?? "nobody yet"} and due{" "}
                      {formatDateTime(task.due_at)}.
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No annotation tasks"
                description="The project currently has no live annotation tasks in view."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Risk posture"
            description={
              escalatedAlerts.length > 0
                ? `${escalatedAlerts.length} escalated alerts need attention alongside the live queue.`
                : "Exception-first context stays alongside project throughput."
            }
          >
            {activeAlerts.length > 0 ? (
              <div className="stack-list">
                {activeAlerts.map((alert) => (
                  <article key={alert.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={describeSeverity(alert.severity)} />
                      <StatusBadge value={alert.status} />
                    </div>
                    <h3>
                      <a className="table-link" href={`/projects/${projectId}/risk/${alert.id}`}>
                        {alert.title}
                      </a>
                    </h3>
                    <p className="muted-text">{alert.summary}</p>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No active alerts"
                description="The project has no live risk alerts right now."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Recent risk-related runs"
            description="Backend workflow runs stay connected to the alert that triggered them."
          >
            {riskRuns.length > 0 ? (
              <div className="stack-list">
                {riskRuns.map((run) => (
                  <a
                    key={run.id}
                    className="stack-item"
                    href={`/workflow-runs/${run.id}`}
                  >
                    <div className="inline-meta">
                      <StatusBadge value={run.status} />
                      <span>{humanizeToken(run.workflow_domain)}</span>
                    </div>
                    <h3>{humanizeToken(run.workflow_type)}</h3>
                    <p className="muted-text">
                      Linked to {run.source_entity_type} {run.source_entity_id}
                    </p>
                  </a>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No risk runs yet"
                description="There are no recent workflow runs tied to project risk."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Recent activity"
            description="Audit evidence stays close to the workspace summary."
          >
            {dashboard.recent_activity.length > 0 ? (
              <div className="timeline-list">
                {dashboard.recent_activity.slice(0, 4).map((item) => (
                  <article key={item.id} className="timeline-item">
                    <h3>
                      {"action" in item
                        ? humanizeToken(item.action)
                        : humanizeToken(item.result_type)}
                    </h3>
                    <p className="muted-text">
                      {"action" in item
                        ? `${item.entity_type} updated in project history.`
                        : `AI result ${humanizeToken(item.status)}.`}
                    </p>
                    <div className="stack-meta">
                      <span>
                        {formatDateTime(
                          "occurred_at" in item ? item.occurred_at : item.reviewed_at,
                        )}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No recent activity"
                description="Project activity will appear here once the backend records events."
              />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
