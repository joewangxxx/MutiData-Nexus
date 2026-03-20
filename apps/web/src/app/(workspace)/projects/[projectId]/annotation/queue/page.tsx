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
  getProjectAnnotationQueue,
  listProjectSourceAssets,
  isControllerApiError,
} from "@/lib/controller-api";
import {
  describePriority,
  formatCount,
  formatDateTime,
  humanizeToken,
} from "@/lib/presenters";
import { AnnotationTaskCreateForm } from "@/components/annotation/annotation-task-create-form";
import { AnnotationTaskQueueClaimButton } from "@/components/annotation/annotation-task-queue-claim-button";

export default async function AnnotationQueuePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [queueData, sourceAssets] = await Promise.all([
    getProjectAnnotationQueue(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    listProjectSourceAssets(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
  ]);

  if (!queueData || !sourceAssets) {
    notFound();
  }

  const inProgressCount = queueData.tasks.filter(
    (task) => ["claimed", "in_progress"].includes(task.status),
  ).length;
  const submittedCount = queueData.tasks.filter((task) => task.status === "submitted").length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Annotation"
        title={`${queueData.project.name} queue`}
        description="Queue-first work surface for annotators with visible priority, due dates, and workflow linkage."
      />

      <MetricGrid>
        <MetricCard
          label="Queue size"
          value={formatCount(queueData.tasks.length)}
          meta="Current visible tasks"
          tone="info"
        />
        <MetricCard
          label="Claimed / in progress"
          value={formatCount(inProgressCount)}
          meta="Tasks already picked up by annotators"
          tone="success"
        />
        <MetricCard
          label="Submitted"
          value={formatCount(submittedCount)}
          meta="Waiting for human review"
          tone="warning"
        />
        <MetricCard
          label="Open workflow runs"
          value={formatCount(queueData.project.counts["active_workflow_runs"])}
          meta="Execution context tied to tasks"
          tone="danger"
        />
      </MetricGrid>

      <SectionCard
        title="Create task"
        description="Thin PM entry for creating a project-scoped annotation task from an existing source asset."
      >
        <AnnotationTaskCreateForm projectId={projectId} sourceAssets={sourceAssets} />
      </SectionCard>

      <SectionCard
        title="Task list"
        description="Approved flow: queue to workbench, with the project context preserved the whole time."
      >
        {queueData.tasks.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Asset</th>
                <th>Assignee</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Due</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {queueData.tasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <a
                      className="table-link"
                      href={`/projects/${projectId}/annotation/tasks/${task.id}`}
                    >
                      {task.id}
                    </a>
                    <div className="table-meta">{humanizeToken(task.task_type)}</div>
                  </td>
                  <td>{task.source_asset?.asset_kind ?? "media item"}</td>
                  <td>{task.assigned_to_user_id ?? "Unassigned"}</td>
                  <td>
                    <StatusBadge value={task.status} />
                  </td>
                  <td>{humanizeToken(describePriority(task.priority))}</td>
                  <td>{formatDateTime(task.due_at)}</td>
                  <td>
                    {task.status === "queued" && !task.assigned_to_user_id ? (
                      <AnnotationTaskQueueClaimButton taskId={task.id} claimable />
                    ) : (
                      <span className="muted-text">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState
            title="Queue is clear"
            description="No annotation tasks are currently waiting in this project."
          />
        )}
      </SectionCard>
    </div>
  );
}
