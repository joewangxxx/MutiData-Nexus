import { PageHeader, SectionCard } from "@/components/ui/primitives";

export default function Loading() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk item detail"
        title="Loading risk alert"
        description="Fetching the current snapshot, source signal, and strategy proposals."
      />
      <div className="metric-grid">
        <article className="surface-card metric-card loading-card" />
        <article className="surface-card metric-card loading-card" />
        <article className="surface-card metric-card loading-card" />
        <article className="surface-card metric-card loading-card" />
      </div>
      <div className="section-grid">
        <div className="span-6">
          <SectionCard title="Risk snapshot">
            <div className="loading-stack">
              <div className="loading-row" />
              <div className="loading-row" />
              <div className="loading-row" />
            </div>
          </SectionCard>
        </div>
        <div className="span-6">
          <SectionCard title="Source signal">
            <div className="loading-stack">
              <div className="loading-row" />
              <div className="loading-row" />
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
