import type { ReactNode } from "react";

function joinClasses(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="page-eyebrow">{eyebrow}</p>
        <h1 className="page-title">{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function MetricGrid({ children }: { children: ReactNode }) {
  return <section className="metric-grid">{children}</section>;
}

export function MetricCard({
  label,
  value,
  meta,
  tone = "default",
}: {
  label: string;
  value: string | number;
  meta: string;
  tone?: "default" | "success" | "warning" | "danger" | "info";
}) {
  return (
    <article className={joinClasses("surface-card", "metric-card", `tone-${tone}`)}>
      <p className="metric-label">{label}</p>
      <strong className="metric-value">{value}</strong>
      <p className="metric-meta">{meta}</p>
    </article>
  );
}

export function SectionCard({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="surface-card section-card">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone = normalized.includes("critical") || normalized.includes("failed")
    || normalized.includes("reject")
    ? "danger"
    : normalized.includes("warning") ||
        normalized.includes("blocked") ||
        normalized.includes("escalated") ||
        normalized.includes("revise")
      ? "warning"
      : normalized.includes("review") ||
          normalized.includes("running") ||
          normalized.includes("progress")
        ? "info"
          : normalized.includes("active") ||
              normalized.includes("approve") ||
              normalized.includes("approved") ||
              normalized.includes("complete") ||
              normalized.includes("succeeded")
          ? "success"
          : "default";

  return <span className={joinClasses("status-badge", `tone-${tone}`)}>{value}</span>;
}

export function KeyValueList({
  items,
}: {
  items: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <dl className="key-value-list">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
