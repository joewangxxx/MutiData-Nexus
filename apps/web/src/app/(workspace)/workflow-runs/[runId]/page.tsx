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
  getWorkflowRunDetail,
  isControllerApiError,
} from "@/lib/controller-api";
import { formatCount, formatDateTime, humanizeToken } from "@/lib/presenters";

export default async function WorkflowRunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const workflowData = await getWorkflowRunDetail(runId).catch((error) => {
    if (isControllerApiError(error) && error.status === 404) {
      return null;
    }

    throw error;
  });

  if (!workflowData) {
    notFound();
  }

  const { project, relatedTask, relatedAlert, run } = workflowData;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workflow detail"
        title={humanizeToken(run.workflow_type)}
        description={`Run ${run.id} stays linked to ${project.name} and the source object that started it.`}
        actions={<StatusBadge value={run.status} />}
      />

      <MetricGrid>
        <MetricCard
          label="Status"
          value={humanizeToken(run.status)}
          meta="Current lifecycle state"
          tone="info"
        />
        <MetricCard
          label="Domain"
          value={humanizeToken(run.workflow_domain)}
          meta="Annotation workflow family"
          tone="success"
        />
        <MetricCard
          label="Coze attempts"
          value={formatCount(run.coze_runs.length)}
          meta="Provider attempts under this run"
          tone="warning"
        />
        <MetricCard
          label="AI results"
          value={formatCount(run.ai_results.length)}
          meta="Persisted outputs from the run"
          tone="danger"
        />
      </MetricGrid>

      <div className="section-grid">
        <div className="span-6">
          <SectionCard
            title="Step timeline"
            description="The run detail keeps the blocked or last successful stage obvious."
          >
            {run.steps.length > 0 ? (
              <div className="timeline-list">
                {run.steps.map((step) => (
                  <article key={step.id} className="timeline-item">
                    <div className="inline-meta">
                      <StatusBadge value={step.status} />
                      <span>Step {step.sequence_no}</span>
                    </div>
                    <h3>{humanizeToken(step.step_key)}</h3>
                    <p className="muted-text">
                      Started {formatDateTime(step.started_at)} and completed{" "}
                      {formatDateTime(step.completed_at)}.
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No workflow steps"
                description="This run has not recorded any timeline entries yet."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Coze attempts"
            description="Provider activity is visible without the frontend ever calling Coze directly."
          >
            {run.coze_runs.length > 0 ? (
              <div className="stack-list">
                {run.coze_runs.map((cozeRun) => (
                  <article key={cozeRun.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={cozeRun.status} />
                      <span>{cozeRun.coze_workflow_key}</span>
                    </div>
                    <h3>{cozeRun.external_run_id ?? "Awaiting external run id"}</h3>
                    <p className="muted-text">
                      Dispatched {formatDateTime(cozeRun.dispatched_at)} with HTTP{" "}
                      {cozeRun.http_status ?? "n/a"}.
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Coze attempts"
                description="The run has not been dispatched to the provider yet."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="AI results"
            description="Persisted outputs stay inspectable before acceptance or rejection."
          >
            {run.ai_results.length > 0 ? (
              <div className="stack-list">
                {run.ai_results.map((result) => (
                  <article key={result.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={result.status} />
                      <span>{humanizeToken(result.result_type)}</span>
                    </div>
                    <h3>{result.id}</h3>
                    <pre className="json-block">
                      {JSON.stringify(result.normalized_payload, null, 2)}
                    </pre>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No AI results yet"
                description="Results will appear here after the backend persists them."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Linked object"
            description="Movement between run detail and the source work object stays explicit."
          >
            {relatedTask ? (
              <div className="stack-item">
                <div className="inline-meta">
                  <StatusBadge value={relatedTask.status} />
                  <span>Annotation task</span>
                </div>
                <h3>{relatedTask.id}</h3>
                <a
                  className="callout-link"
                  href={`/projects/${project.id}/annotation/tasks/${relatedTask.id}`}
                >
                  Open task workbench
                </a>
              </div>
            ) : relatedAlert ? (
              <div className="stack-item">
                <div className="inline-meta">
                  <StatusBadge value={relatedAlert.status} />
                  <span>{humanizeToken(relatedAlert.risk_signal?.signal_type ?? "risk alert")}</span>
                </div>
                <h3>{relatedAlert.title}</h3>
                <p className="muted-text">{relatedAlert.summary}</p>
                <a
                  className="callout-link"
                  href={`/projects/${project.id}/risk/${relatedAlert.id}`}
                >
                  Open risk alert detail
                </a>
              </div>
            ) : (
              <EmptyState
                title="No linked object"
                description="This run is not attached to the annotation or risk slice."
              />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
