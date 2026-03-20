import { PageHeader, SectionCard } from "@/components/ui/primitives";

export default function Loading() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Risk monitor"
        title="Loading project risk dashboard"
        description="Fetching live alerts and signals from the controller."
      />
      <div className="metric-grid">
        <article className="surface-card metric-card loading-card" />
        <article className="surface-card metric-card loading-card" />
        <article className="surface-card metric-card loading-card" />
        <article className="surface-card metric-card loading-card" />
      </div>
      <div className="section-grid">
        <div className="span-7">
          <SectionCard title="Live alerts">
            <div className="loading-stack">
              <div className="loading-row" />
              <div className="loading-row" />
              <div className="loading-row" />
            </div>
          </SectionCard>
        </div>
        <div className="span-5">
          <SectionCard title="Latest signals">
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
