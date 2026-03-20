import { notFound } from "next/navigation";

import { AnnotationTaskReviewControls } from "@/components/annotation/annotation-task-review-controls";
import { AnnotationTaskWorkbenchActions } from "@/components/annotation/annotation-task-workbench-actions";
import { AnnotationTaskManagementPanel } from "@/components/annotation/annotation-task-management-panel";
import { AnnotationSourceAssetPreview } from "@/components/annotation/annotation-source-asset-preview";
import {
  EmptyState,
  MetricCard,
  MetricGrid,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui/primitives";
import {
  getAnnotationWorkbench,
  getSourceAssetAccess,
  isControllerApiError,
} from "@/lib/controller-api";
import {
  describePriority,
  formatCount,
  formatDateTime,
  humanizeToken,
} from "@/lib/presenters";

export default async function AnnotationTaskPage({
  params,
}: {
  params: Promise<{ projectId: string; taskId: string }>;
}) {
  const { projectId, taskId } = await params;
  const taskData = await getAnnotationWorkbench(projectId, taskId).catch((error) => {
    if (isControllerApiError(error) && error.status === 404) {
      return null;
    }

    throw error;
  });

  if (!taskData) {
    notFound();
  }

  const sourceAssetAccess = await getSourceAssetAccess(taskData.sourceAsset.id).catch(() => ({
    asset_id: taskData.sourceAsset.id,
    project_id: taskData.sourceAsset.project_id,
    dataset_id: taskData.sourceAsset.dataset_id,
    asset_kind: taskData.sourceAsset.asset_kind,
    delivery_type: "direct_uri",
    uri: taskData.sourceAsset.uri,
    mime_type: taskData.sourceAsset.mime_type,
  }));

  const initialLabels = taskData.revisions[0]?.labels ?? [];
  const outputSummary = taskData.task.output_payload["summary"];
  const initialContent =
    typeof outputSummary === "string"
      ? outputSummary
      : taskData.task.output_payload && Object.keys(taskData.task.output_payload).length > 0
        ? JSON.stringify(taskData.task.output_payload, null, 2)
        : "";
  const latestReview = taskData.reviews[0] ?? null;
  const canReview = ["submitted", "needs_review"].includes(taskData.task.status);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Annotation workbench"
        title={taskData.task.id}
        description={`${taskData.project.name} task for ${humanizeToken(taskData.task.task_type)}.`}
        actions={<StatusBadge value={taskData.task.status} />}
      />

      <MetricGrid>
        <MetricCard
          label="Status"
          value={humanizeToken(taskData.task.status)}
          meta="Current task lifecycle"
          tone="info"
        />
        <MetricCard
          label="Priority"
          value={humanizeToken(describePriority(taskData.task.priority))}
          meta="Escalation and SLA hint"
          tone="warning"
        />
        <MetricCard
          label="AI suggestions"
          value={formatCount(taskData.aiSuggestions.length)}
          meta="Persisted suggestion records"
          tone="success"
        />
        <MetricCard
          label="Revisions"
          value={formatCount(taskData.revisions.length)}
          meta="Submission and draft history"
          tone="danger"
        />
      </MetricGrid>

      <div className="section-grid">
        <div className="span-12">
          <SectionCard
            title="Task management"
            description="Thin control surface for assignment, due date, priority, and lifecycle state."
          >
            <AnnotationTaskManagementPanel task={taskData.task} />
          </SectionCard>
        </div>

        <div className="span-12">
          <SectionCard
            title="Submission controls"
            description="Generate suggestions or submit a revision against the live annotation contract."
          >
            <AnnotationTaskWorkbenchActions
              taskId={taskData.task.id}
              initialLabels={initialLabels}
              initialContent={initialContent}
            />
          </SectionCard>
        </div>

        <div className="span-4">
          <SectionCard
            title="Source asset"
            description="Underlying media remains visible inside the same project context."
          >
            <AnnotationSourceAssetPreview
              asset={taskData.sourceAsset}
              access={sourceAssetAccess}
            />
          </SectionCard>
        </div>

        <div className="span-4">
          <SectionCard
            title="Instructions"
            description="Task instructions, schema, and draft output stay together in the workbench."
          >
            <pre className="json-block">
              {JSON.stringify(taskData.task.annotation_schema, null, 2)}
            </pre>
            <pre className="json-block">
              {JSON.stringify(taskData.task.output_payload, null, 2)}
            </pre>
          </SectionCard>
        </div>

        <div className="span-4">
          <SectionCard
            title="AI suggestions"
            description="Low-confidence or review-required suggestions remain visibly optional."
          >
            {taskData.aiSuggestions.length > 0 ? (
              <div className="stack-list">
                {taskData.aiSuggestions.map((suggestion) => (
                  <article key={suggestion.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={suggestion.status} />
                      <span>{humanizeToken(suggestion.result_type)}</span>
                    </div>
                    <pre className="json-block">
                      {JSON.stringify(suggestion.normalized_payload, null, 2)}
                    </pre>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No AI suggestions yet"
                description="Generate a live suggestion to populate this panel."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Revision history"
            description="The detail page preserves a visible trail of changes and notes."
          >
            {taskData.revisions.length > 0 ? (
              <div className="timeline-list">
                {taskData.revisions.map((revision) => (
                  <article key={revision.id} className="timeline-item">
                    <div className="inline-meta">
                      <StatusBadge value={revision.revision_kind} />
                      <span>Revision {revision.revision_no}</span>
                    </div>
                    <h3>{revision.labels.join(", ") || "No labels yet"}</h3>
                    <p className="muted-text">Created {formatDateTime(revision.created_at)}</p>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No revisions yet"
                description="Submit the first revision to start the history trail."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Review history"
            description="Reviewer decisions stay attached to the submitted revision and the task lifecycle."
          >
            {taskData.reviews.length > 0 ? (
              <div className="stack-list">
                {latestReview ? (
                  <article className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={latestReview.decision} />
                      <span>Latest review</span>
                    </div>
                    <h3>{latestReview.revision_id}</h3>
                    <p className="muted-text">
                      Reviewed by {latestReview.reviewed_by_user_id} at{" "}
                      {formatDateTime(latestReview.created_at)}.
                    </p>
                    {latestReview.notes ? <p className="muted-text">{latestReview.notes}</p> : null}
                  </article>
                ) : null}
                <div className="timeline-list">
                  {taskData.reviews
                    .filter((review) => review.id !== latestReview?.id)
                    .map((review) => (
                    <article key={review.id} className="timeline-item">
                      <div className="inline-meta">
                        <StatusBadge value={review.decision} />
                        <span>{review.revision_id}</span>
                      </div>
                      <h3>{review.id}</h3>
                      <p className="muted-text">
                        Reviewed by {review.reviewed_by_user_id} at{" "}
                        {formatDateTime(review.created_at)}.
                      </p>
                      {review.notes ? <p className="muted-text">{review.notes}</p> : null}
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState
                title="No reviews yet"
                description="The task is waiting for a reviewer decision."
              />
            )}

            {canReview && taskData.revisions.length > 0 ? (
              <div className="stack-list">
                <h3>Reviewer controls</h3>
                <AnnotationTaskReviewControls
                  taskId={taskData.task.id}
                  revisions={taskData.revisions}
                />
              </div>
            ) : null}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Linked workflow"
            description="Users can inspect execution state without losing the task back path."
          >
            {taskData.linkedRun ? (
              <article className="stack-item">
                <div className="inline-meta">
                  <StatusBadge value={taskData.linkedRun.status} />
                  <span>{humanizeToken(taskData.linkedRun.workflow_type)}</span>
                </div>
                <h3>{taskData.linkedRun.id}</h3>
                <p className="muted-text">
                  Started {formatDateTime(taskData.linkedRun.started_at)}
                </p>
                <a
                  className="callout-link"
                  href={`/workflow-runs/${taskData.linkedRun.id}`}
                >
                  Open workflow detail
                </a>
              </article>
            ) : (
              <EmptyState
                title="No workflow linked"
                description="This task currently has no workflow run attached."
              />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
