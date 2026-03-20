import { notFound } from "next/navigation";

import {
  EmptyState,
  MetricCard,
  MetricGrid,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui/primitives";
import { getProjectRiskOverview, isControllerApiError } from "@/lib/controller-api";
import { describeSeverity, formatCount, formatDateTime, humanizeToken } from "@/lib/presenters";
import { ProjectRiskCaptureForm } from "@/components/risk/project-risk-capture-form";

export default async function ProjectRiskPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const riskData = await getProjectRiskOverview(projectId).catch((error) => {
    if (isControllerApiError(error) && error.status === 404) {
      return null;
    }

    throw error;
  });

  if (!riskData) {
    notFound();
  }

  const openAlertsCount = riskData.alerts.filter(
    (alert) => !["resolved", "dismissed"].includes(alert.status),
  ).length;
  const escalatedCount = riskData.alerts.filter((alert) => alert.status === "escalated").length;
  const activeSignalsCount = riskData.signals.filter((signal) =>
    ["open", "active", "triaged"].includes(signal.status),
  ).length;
  const linkedWorkflowCount = riskData.alerts.filter(
    (alert) => alert.detected_by_workflow_run_id,
  ).length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk monitor"
        title={`${riskData.project.name} live risk dashboard`}
        description="Controller-backed risk snapshots and signals stay tied to the project workspace."
        actions={
          <div className="button-row">
            <a className="button-secondary" href={`/projects/${projectId}`}>
              Back to project
            </a>
          </div>
        }
      />

      <MetricGrid>
        <MetricCard
          label="Open alerts"
          value={formatCount(openAlertsCount)}
          meta="Current risk snapshots in scope"
          tone="warning"
        />
        <MetricCard
          label="Escalated"
          value={formatCount(escalatedCount)}
          meta="Items needing the fastest response"
          tone="danger"
        />
        <MetricCard
          label="Signals"
          value={formatCount(activeSignalsCount)}
          meta="Currently open or active events"
          tone="info"
        />
        <MetricCard
          label="Workflow links"
          value={formatCount(linkedWorkflowCount)}
          meta="Alerts already tied to a backend run"
          tone="success"
        />
      </MetricGrid>

      <SectionCard
        title="Capture risk input"
        description="Save a project signal on its own or save it and trigger analysis from the same form."
      >
        <ProjectRiskCaptureForm projectId={projectId} />
      </SectionCard>

      <div className="section-grid">
        <div className="span-7">
          <SectionCard
            title="Live alerts"
            description="Each row drills into the alert detail page, which stays synced to the current risk snapshot."
          >
            {riskData.alerts.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Alert</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Workflow</th>
                    <th>Next review</th>
                  </tr>
                </thead>
                <tbody>
                  {riskData.alerts.map((alert) => (
                    <tr key={alert.id}>
                      <td>
                        <a
                          className="table-link"
                          href={`/projects/${projectId}/risk/${alert.id}`}
                        >
                          {alert.title}
                        </a>
                        <div className="table-meta">{alert.summary}</div>
                      </td>
                      <td>
                        <div className="stack-meta">
                          <StatusBadge value={describeSeverity(alert.severity)} />
                          <span>{formatCount(alert.severity)}</span>
                        </div>
                      </td>
                      <td>
                        <StatusBadge value={alert.status} />
                      </td>
                      <td>
                        {alert.detected_by_workflow_run_id ? (
                          <a
                            className="table-link"
                            href={`/workflow-runs/${alert.detected_by_workflow_run_id}`}
                          >
                            {alert.detected_by_workflow_run_id}
                          </a>
                        ) : (
                          "Not linked"
                        )}
                      </td>
                      <td>{formatDateTime(alert.next_review_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState
                title="No live alerts"
                description="The project has no open or escalated risk alerts yet."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-5">
          <SectionCard
            title="Latest signals"
            description="Risk signals are the ingest layer that can later become alerts."
          >
            {riskData.signals.length > 0 ? (
              <div className="stack-list">
                {riskData.signals.map((signal) => (
                  <article key={signal.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={signal.status} />
                      <span>{humanizeToken(signal.signal_type)}</span>
                    </div>
                    <h3>{signal.title}</h3>
                    <p className="muted-text">{signal.description ?? "No description provided."}</p>
                    <div className="stack-meta">
                      <span>{describeSeverity(signal.severity)}</span>
                      <span>{formatDateTime(signal.observed_at)}</span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No live signals"
                description="The project has not ingested any risk signals yet."
              />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
