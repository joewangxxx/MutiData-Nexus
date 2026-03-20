import {
  KeyValueList,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui/primitives";
import { listVisibleProjects } from "@/lib/mock-adapters";
import { formatCount } from "@/lib/presenters";

export default async function ProjectsPage() {
  const projects = await listVisibleProjects();

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Projects"
        title="Portfolio workspace"
        description="Browse the shared project anchor for annotation, risk, workflow status, and recent ownership changes."
      />

      <div className="section-grid">
        {projects.map((project) => (
          <div key={project.id} className="span-6">
            <SectionCard
              title={project.name}
              description={project.description ?? "No description available."}
              action={<StatusBadge value={project.status} />}
            >
              <KeyValueList
                items={[
                  { label: "Project code", value: project.code },
                  {
                    label: "Annotation queue",
                    value: formatCount(project.counts.annotation_queue),
                  },
                  {
                    label: "Risk queue",
                    value: formatCount(project.counts.risk_queue),
                  },
                  {
                    label: "Waiting for human",
                    value: formatCount(project.counts.waiting_for_human_runs),
                  },
                ]}
              />
              <div className="button-row">
                <a className="button-primary" href={`/projects/${project.id}`}>
                  Open project
                </a>
                <a
                  className="button-secondary"
                  href={`/projects/${project.id}/annotation/queue`}
                >
                  Annotation queue
                </a>
                <a className="button-secondary" href={`/projects/${project.id}/risk`}>
                  Risk dashboard
                </a>
              </div>
            </SectionCard>
          </div>
        ))}
      </div>
    </div>
  );
}
