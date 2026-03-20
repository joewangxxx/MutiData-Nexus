import { notFound } from "next/navigation";

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
  DatasetMutationForm,
  SourceAssetMutationForm,
} from "@/components/catalog/catalog-mutation-forms";
import {
  getProject,
  getSourceAssetAccess,
  isControllerApiError,
  listProjectDatasets,
  listProjectSourceAssets,
} from "@/lib/controller-api";
import { formatCount, formatDateTime, humanizeToken } from "@/lib/presenters";

function formatAssetAccessDetails(asset: {
  delivery_type: string;
  mime_type: string | null;
}) {
  return `${asset.delivery_type}${asset.mime_type ? ` | ${asset.mime_type}` : ""}`;
}

function formatAssetTechnicalDetails(asset: {
  storage_key: string;
  checksum: string;
  duration_ms: number | null;
  width_px: number | null;
  height_px: number | null;
  frame_rate: number | null;
  transcript: string | null;
}) {
  const details: string[] = [];

  if (asset.storage_key) {
    details.push(asset.storage_key);
  }
  if (asset.checksum) {
    details.push(asset.checksum);
  }
  if (asset.duration_ms !== null) {
    details.push(`${formatCount(asset.duration_ms)} ms`);
  }
  if (asset.width_px !== null && asset.height_px !== null) {
    details.push(`${formatCount(asset.width_px)} x ${formatCount(asset.height_px)}`);
  }
  if (asset.frame_rate !== null) {
    details.push(`${asset.frame_rate} fps`);
  }
  if (asset.transcript) {
    details.push("Transcript available");
  }

  return details.length > 0 ? details.join(" | ") : "Metadata only";
}

export default async function ProjectCatalogPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [project, datasets, assets] = await Promise.all([
    getProject(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    listProjectDatasets(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
    listProjectSourceAssets(projectId).catch((error) => {
      if (isControllerApiError(error) && error.status === 404) {
        return null;
      }

      throw error;
    }),
  ]);

  if (!project || !datasets || !assets) {
    notFound();
  }

  const assetsByDatasetId = new Map<string, typeof assets>();
  datasets.forEach((dataset) => {
    assetsByDatasetId.set(
      dataset.id,
      assets.filter((asset) => asset.dataset_id === dataset.id),
    );
  });

  const unassignedAssets = assets.filter((asset) => !asset.dataset_id);
  const imageCount = assets.filter((asset) => asset.asset_kind === "image").length;
  const audioCount = assets.filter((asset) => asset.asset_kind === "audio").length;
  const videoCount = assets.filter((asset) => asset.asset_kind === "video").length;
  const assetAccessEntries = await Promise.all(
    assets.map(async (asset) => {
      try {
        return await getSourceAssetAccess(asset.id);
      } catch {
        return null;
      }
    }),
  );
  const assetAccessById = new Map(
    assetAccessEntries
      .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
      .map((entry) => [entry.asset_id, entry]),
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Catalog"
        title={`${project.name} catalog`}
        description="Live catalog for project datasets and source assets with metadata registration and update through the platform API."
        actions={
          <div className="button-row">
            <a className="button-secondary" href={`/projects/${projectId}`}>
              Back to project
            </a>
          </div>
        }
      />

      <div className="section-grid">
        <div className="span-6">
          <SectionCard
            title="Create dataset"
            description="Register a project-scoped dataset metadata record without uploading files."
          >
            <DatasetMutationForm projectId={projectId} />
          </SectionCard>
        </div>
        <div className="span-6">
          <SectionCard
            title="Register source asset"
            description="Register a project-scoped image, audio, or video asset and optionally attach it to a dataset."
          >
            <SourceAssetMutationForm projectId={projectId} datasets={datasets} />
          </SectionCard>
        </div>
      </div>

      <MetricGrid>
        <MetricCard
          label="Datasets"
          value={formatCount(datasets.length)}
          meta="Project-scoped containers in live view"
          tone="info"
        />
        <MetricCard
          label="Source assets"
          value={formatCount(assets.length)}
          meta="Multimodal items currently indexed"
          tone="success"
        />
        <MetricCard
          label="Unassigned assets"
          value={formatCount(unassignedAssets.length)}
          meta="Media not linked to a dataset"
          tone="warning"
        />
        <MetricCard
          label="Modalities"
          value={`${formatCount(imageCount)} / ${formatCount(audioCount)} / ${formatCount(videoCount)}`}
          meta="Image / audio / video"
          tone="default"
        />
      </MetricGrid>

      <SectionCard
        title="Project context"
        description="The catalog stays anchored to the current project and its controller-owned metadata."
      >
        <KeyValueList
          items={[
            { label: "Code", value: project.code },
            { label: "Status", value: <StatusBadge value={project.status} /> },
            {
              label: "Owner user",
              value: project.owner_user_id,
            },
            {
              label: "Source kinds",
              value:
                datasets.length > 0
                  ? Array.from(new Set(datasets.map((dataset) => humanizeToken(dataset.source_kind)))).join(
                      ", ",
                    )
                  : "Not available",
            },
          ]}
        />
      </SectionCard>

      <SectionCard
        title="Dataset overview"
        description="Each dataset remains a live metadata container for the assets indexed under the project."
      >
        {datasets.length > 0 ? (
          <div className="stack-list">
            {datasets.map((dataset) => {
              const datasetAssets = assetsByDatasetId.get(dataset.id) ?? [];

              return (
                <article key={dataset.id} className="stack-item">
                  <div className="inline-meta">
                    <StatusBadge value={dataset.status} />
                    <StatusBadge value={humanizeToken(dataset.source_kind)} />
                  </div>
                  <h3>{dataset.name}</h3>
                  <p className="muted-text">
                    {dataset.description ?? "No dataset description provided."}
                  </p>
                  <div className="stack-meta">
                    <span>{formatCount(datasetAssets.length)} assets</span>
                    <span>Created {formatDateTime(dataset.created_at)}</span>
                    <span>
                      {dataset.archived_at ? `Archived ${formatDateTime(dataset.archived_at)}` : "Active"}
                    </span>
                  </div>
                  <details className="stack-list">
                    <summary className="table-link">Edit dataset metadata</summary>
                    <DatasetMutationForm projectId={projectId} dataset={dataset} />
                  </details>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="No datasets yet"
            description="This project has no live datasets in the controller-backed catalog."
          />
        )}
      </SectionCard>

      <SectionCard
        title="Source asset list"
        description="Modalities, dataset ties, and backend-owned access entry information stay visible alongside metadata updates."
      >
        {assets.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Modality</th>
                <th>Dataset</th>
                <th>Access entry</th>
                <th>Details</th>
                <th>Manage</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => {
                const dataset = datasets.find((entry) => entry.id === asset.dataset_id);
                const access = assetAccessById.get(asset.id);

                return (
                  <tr key={asset.id}>
                    <td>
                      <a className="table-link" href={access?.uri ?? asset.uri}>
                        {asset.id}
                      </a>
                      <div className="table-meta">{asset.mime_type}</div>
                    </td>
                    <td>
                      <StatusBadge value={asset.asset_kind} />
                    </td>
                    <td>
                      {dataset ? (
                        <>
                          <div>{dataset.name}</div>
                          <div className="table-meta">{dataset.status}</div>
                        </>
                      ) : (
                        "Unassigned"
                      )}
                    </td>
                    <td>
                      <a className="table-link" href={access?.uri ?? asset.uri}>
                        Open source URI
                      </a>
                      <div className="table-meta">
                        {formatAssetAccessDetails(
                          access ?? {
                            delivery_type: "direct_uri",
                            mime_type: asset.mime_type,
                          },
                        )}
                      </div>
                    </td>
                    <td>{formatAssetTechnicalDetails(asset)}</td>
                    <td>
                      <details>
                        <summary className="table-link">Edit metadata</summary>
                        <SourceAssetMutationForm
                          projectId={projectId}
                          datasets={datasets}
                          asset={asset}
                        />
                      </details>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <EmptyState
            title="No source assets yet"
            description="The project catalog currently has no live multimodal assets."
          />
        )}
      </SectionCard>
    </div>
  );
}
