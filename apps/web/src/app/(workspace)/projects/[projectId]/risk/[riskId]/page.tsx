import { notFound } from "next/navigation";

import { RiskStrategyDecisionActions } from "@/components/risk/risk-strategy-decision-actions";
import { RiskAlertActions } from "@/components/risk/risk-alert-actions";
import {
  EmptyState,
  KeyValueList,
  MetricCard,
  MetricGrid,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui/primitives";
import {
  getProject,
  getRiskAlertDetail,
  isControllerApiError,
} from "@/lib/controller-api";
import { describeSeverity, formatDateTime, humanizeToken } from "@/lib/presenters";

export default async function ProjectRiskAlertPage({
  params,
}: {
  params: Promise<{ projectId: string; riskId: string }>;
}) {
  const { projectId, riskId } = await params;
  const [project, alert] = await Promise.all([
    getProject(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    getRiskAlertDetail(riskId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
  ]);

  if (!project || !alert || alert.project_id !== project.id) {
    notFound();
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk item detail"
        title={alert.title}
        description={alert.summary}
        actions={
          <div className="button-row">
            <a className="button-secondary" href={`/projects/${projectId}/risk`}>
              Back to risk dashboard
            </a>
            <a className="button-secondary" href={`/projects/${projectId}`}>
              Project overview
            </a>
          </div>
        }
      />

      <MetricGrid>
        <MetricCard
          label="Severity"
          value={alert.severity}
          meta={describeSeverity(alert.severity)}
          tone="warning"
        />
        <MetricCard
          label="Status"
          value={humanizeToken(alert.status)}
          meta="Current risk snapshot state"
          tone="info"
        />
        <MetricCard
          label="Source signal"
          value={humanizeToken(alert.risk_signal?.signal_type ?? "unknown")}
          meta={alert.risk_signal ? alert.risk_signal.title : "No signal attached"}
          tone="success"
        />
        <MetricCard
          label="Strategies"
          value={alert.strategies.length}
          meta="Persisted mitigation proposals"
          tone="danger"
        />
      </MetricGrid>

      <div className="section-grid">
        <div className="span-12">
          <SectionCard
            title="Alert management"
            description="Thin operational controls for the current risk snapshot stay attached to this detail page."
          >
            <RiskAlertActions alert={alert} />
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Risk snapshot"
            description="The alert keeps the current state that the workflow run and dashboard both point to."
          >
            <KeyValueList
              items={[
                { label: "Project", value: project.name },
                { label: "Alert id", value: alert.id },
                { label: "Risk signal id", value: alert.risk_signal_id },
                { label: "Assigned to", value: alert.assigned_to_user_id ?? "Unassigned" },
                { label: "Detected run", value: alert.detected_by_workflow_run_id ?? "Not linked" },
                { label: "Next review", value: formatDateTime(alert.next_review_at) },
              ]}
            />
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Source signal"
            description="The input event that can later escalate into this current risk snapshot."
          >
            {alert.risk_signal ? (
              <div className="stack-list">
                <article className="stack-item">
                  <div className="inline-meta">
                    <StatusBadge value={alert.risk_signal.status} />
                    <span>{humanizeToken(alert.risk_signal.source_kind)}</span>
                  </div>
                  <h3>{alert.risk_signal.title}</h3>
                  <p className="muted-text">
                    {alert.risk_signal.description ?? "No description provided."}
                  </p>
                  <div className="stack-meta">
                    <span>{humanizeToken(alert.risk_signal.signal_type)}</span>
                    <span>{formatDateTime(alert.risk_signal.observed_at)}</span>
                  </div>
                  <pre className="json-block">
                    {JSON.stringify(alert.risk_signal.signal_payload, null, 2)}
                  </pre>
                </article>
              </div>
            ) : (
              <EmptyState
                title="No source signal"
                description="This alert has not been hydrated with its origin signal yet."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Strategy proposals"
            description="Strategy proposals are created by the project risk workflow and appear here automatically."
          >
            {alert.strategies.length > 0 ? (
              <div className="stack-list">
                {alert.strategies.map((strategy) => (
                  <article key={strategy.id} className="stack-item">
                    <div className="inline-meta">
                      <StatusBadge value={strategy.status} />
                      <span>Proposal {strategy.proposal_order}</span>
                    </div>
                    <h3>{strategy.title}</h3>
                    <p className="muted-text">{strategy.summary}</p>
                    <RiskStrategyDecisionActions strategy={strategy} />
                    <pre className="json-block">
                      {JSON.stringify(strategy.strategy_payload, null, 2)}
                    </pre>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No strategies yet"
                description="Run the project risk workflow and the resulting mitigation proposals will appear here automatically."
              />
            )}
          </SectionCard>
        </div>

        <div className="span-6">
          <SectionCard
            title="Workflow drilldown"
            description="Jump between the alert and the workflow run that detected or generated it."
          >
            {alert.detected_by_workflow_run_id ? (
              <div className="stack-item">
                <div className="inline-meta">
                  <StatusBadge value={alert.status} />
                  <span>{describeSeverity(alert.severity)}</span>
                </div>
                <h3>{alert.detected_by_workflow_run_id}</h3>
                <a
                  className="callout-link"
                  href={`/workflow-runs/${alert.detected_by_workflow_run_id}`}
                >
                  Open workflow run detail
                </a>
              </div>
            ) : (
              <EmptyState
                title="No workflow link"
                description="The backend has not attached a run to this alert yet."
              />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
