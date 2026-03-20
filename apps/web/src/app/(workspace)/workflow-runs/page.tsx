import { MetricCard, MetricGrid, PageHeader, SectionCard, StatusBadge } from "@/components/ui/primitives";
import { listWorkflowRuns } from "@/lib/controller-api";
import { formatCount, formatDateTime, humanizeToken } from "@/lib/presenters";

export default async function WorkflowRunsPage() {
  const runs = await listWorkflowRuns();
  const runningCount = runs.filter((run) => run.status === "running").length;
  const waitingCount = runs.filter((run) => run.status === "waiting_for_human").length;
  const failedCount = runs.filter((run) => run.status === "failed").length;
  const succeededCount = runs.filter((run) => run.status === "succeeded").length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workflow runs"
        title="Execution status ledger"
        description="Inspect backend-owned workflow progress without losing the link back to the originating task or risk item."
      />

      <MetricGrid>
        <MetricCard label="Running" value={formatCount(runningCount)} meta="Currently executing" tone="info" />
        <MetricCard label="Waiting for human" value={formatCount(waitingCount)} meta="Approval boundary visible" tone="warning" />
        <MetricCard label="Failed" value={formatCount(failedCount)} meta="Needs recovery or retry" tone="danger" />
        <MetricCard label="Succeeded" value={formatCount(succeededCount)} meta="Completed and persisted" tone="success" />
      </MetricGrid>

      <SectionCard
        title="Run list"
        description="Tier 1 workflow inspection surface aligned to the approved route family."
      >
        <table className="data-table">
          <thead>
            <tr>
              <th>Workflow</th>
              <th>Project</th>
              <th>Related object</th>
              <th>Status</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <a className="table-link" href={`/workflow-runs/${run.id}`}>
                    {humanizeToken(run.workflow_type)}
                  </a>
                  <div className="table-meta">{humanizeToken(run.workflow_domain)}</div>
                </td>
                <td>{run.project_name}</td>
                <td>
                  {run.source_entity_type}: {run.source_entity_id}
                </td>
                <td>
                  <StatusBadge value={run.status} />
                </td>
                <td>{formatDateTime(run.started_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>
    </div>
  );
}
