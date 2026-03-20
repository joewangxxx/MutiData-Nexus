import {
  KeyValueList,
  MetricCard,
  MetricGrid,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui/primitives";
import { getDashboardLanding } from "@/lib/mock-adapters";
import { formatCount, formatDateTime, humanizeToken } from "@/lib/presenters";

export default async function DashboardPage() {
  const { dashboard, focusProject, inboxItems, projects, shell } =
    await getDashboardLanding();

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Role dashboard"
        title={`Welcome back, ${shell.currentUser.displayName}`}
        description="One operating surface for annotation throughput, risk posture, and workflow health."
        actions={
          <div className="button-row">
            <a className="button-primary" href={`/projects/${focusProject.id}`}>
              Open focus project
            </a>
            <a
              className="button-secondary"
              href={`/projects/${focusProject.id}/annotation/queue`}
            >
              Jump to queue
            </a>
          </div>
        }
      />

      <MetricGrid>
        <MetricCard
          label="Assigned tasks"
          value={formatCount(dashboard.inbox.assigned_tasks)}
          meta={`Current user actions inside ${focusProject.name}`}
          tone="info"
        />
        <MetricCard
          label="Open alerts"
          value={formatCount(dashboard.inbox.open_alerts)}
          meta="Risk items still waiting on a decision"
          tone="warning"
        />
        <MetricCard
          label="Pending approvals"
          value={formatCount(dashboard.inbox.pending_approvals)}
          meta="Human approval boundaries still open"
          tone="danger"
        />
        <MetricCard
          label="Active runs"
          value={formatCount(dashboard.workload.active_runs)}
          meta="Cross-workflow execution currently in flight"
          tone="success"
        />
      </MetricGrid>

      <div className="section-grid">
        <div className="span-7">
          <SectionCard
            title="Projects in motion"
            description="The left rail stays stable, but projects remain the anchor object."
          >
            <div className="stack-list">
              {projects.map((project) => (
                <article key={project.id} className="stack-item">
                  <div className="section-heading">
                    <div>
                      <h3>{project.name}</h3>
                      <p>{project.description}</p>
                    </div>
                    <StatusBadge value={project.status} />
                  </div>
                  <KeyValueList
                    items={[
                      {
                        label: "Annotation queue",
                        value: formatCount(project.counts.annotation_queue),
                      },
                      {
                        label: "Risk queue",
                        value: formatCount(project.counts.risk_queue),
                      },
                      {
                        label: "Active runs",
                        value: formatCount(project.counts.active_workflow_runs),
                      },
                    ]}
                  />
                  <div className="button-row">
                    <a className="callout-link" href={`/projects/${project.id}`}>
                      Project overview
                    </a>
                    <a
                      className="callout-link"
                      href={`/projects/${project.id}/risk`}
                    >
                      Risk monitor
                    </a>
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>

        <div className="span-5">
          <SectionCard
            title="Inbox focus"
            description="A shared triage surface built from approved task, risk, and workflow objects."
          >
            <div className="action-list">
              {inboxItems.map((item) => (
                <a key={item.id} className="action-item" href={item.href}>
                  <div className="inline-meta">
                    <StatusBadge value={item.status} />
                    <span>{item.projectName}</span>
                  </div>
                  <h3>{item.title}</h3>
                  <p className="muted-text">{item.summary}</p>
                </a>
              ))}
            </div>
          </SectionCard>
        </div>

        <div className="span-12">
          <SectionCard
            title="Recent activity"
            description="Audit entries and AI results stay visible beside the work, not buried in a separate admin surface."
          >
            <div className="timeline-list">
              {dashboard.recent_activity.map((item) => (
                <article
                  key={item.id}
                  className="timeline-item"
                >
                  <h3>
                    {"action" in item ? humanizeToken(item.action) : humanizeToken(item.result_type)}
                  </h3>
                  <p className="muted-text">
                    {"action" in item
                      ? `Entity ${item.entity_type} changed state.`
                      : `AI result ${humanizeToken(item.status)} for ${item.source_entity_type}.`}
                  </p>
                  <div className="inline-meta">
                    <StatusBadge value={"action" in item ? item.action : item.status} />
                    <span>
                      {formatDateTime(
                        "occurred_at" in item ? item.occurred_at : item.reviewed_at,
                      )}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
