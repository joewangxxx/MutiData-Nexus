import { MetricCard, MetricGrid, PageHeader, SectionCard, StatusBadge } from "@/components/ui/primitives";
import { listInboxItems } from "@/lib/mock-adapters";
import { formatCount, humanizeToken } from "@/lib/presenters";

export default async function InboxPage() {
  const items = await listInboxItems();
  const taskCount = items.filter((item) => item.kind === "task").length;
  const riskCount = items.filter((item) => item.kind === "risk").length;
  const workflowCount = items.filter((item) => item.kind === "workflow").length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Inbox"
        title="Cross-role action queue"
        description="Approvals, alerts, and stalled workflows all resolve back to their originating objects from here."
      />

      <MetricGrid>
        <MetricCard label="Inbox items" value={formatCount(items.length)} meta="Current actionable queue" tone="info" />
        <MetricCard label="Task actions" value={formatCount(taskCount)} meta="Annotation work needing progress" tone="success" />
        <MetricCard label="Risk actions" value={formatCount(riskCount)} meta="Exceptions waiting on a PM decision" tone="warning" />
        <MetricCard label="Workflow blockers" value={formatCount(workflowCount)} meta="Runs needing inspection or retry" tone="danger" />
      </MetricGrid>

      <SectionCard
        title="Action list"
        description="This page uses a derived frontend view model because the v1 contract defines the source objects but not a dedicated inbox endpoint."
      >
        <div className="action-list">
          {items.map((item) => (
            <a key={item.id} className="action-item" href={item.href}>
              <div className="inline-meta">
                <StatusBadge value={item.status} />
                <span>{item.projectName}</span>
                <span>{humanizeToken(item.kind)}</span>
              </div>
              <h3>{item.title}</h3>
              <p className="muted-text">{item.summary}</p>
            </a>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
