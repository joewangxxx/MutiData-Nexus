"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import type { Dataset, SourceAsset } from "@/lib/contracts";

function compactObject<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined && item !== ""),
  ) as T;
}

function parseJsonRecord(value: string): Record<string, unknown> {
  if (!value.trim()) {
    return {};
  }

  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Metadata must be a JSON object.");
  }

  return parsed as Record<string, unknown>;
}

function toOptionalNumber(value: string): number | undefined {
  if (!value.trim()) {
    return undefined;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

async function requestJson(path: string, method: "POST" | "PATCH", body: Record<string, unknown>) {
  const response = await fetch(path, {
    method,
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const text = await response.text();
  let payload: { error?: { message?: string } } | null = null;

  if (text) {
    try {
      payload = JSON.parse(text) as { error?: { message?: string } };
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    throw new Error(
      payload?.error?.message ?? `Request to ${path} failed with status ${response.status}.`,
    );
  }

  return payload;
}

type DatasetMutationFormProps = {
  projectId: string;
  dataset?: Dataset;
};

export function DatasetMutationForm({ projectId, dataset }: DatasetMutationFormProps) {
  const router = useRouter();
  const isEditing = Boolean(dataset);
  const datasetId = dataset?.id;
  const [name, setName] = useState(dataset?.name ?? "");
  const [sourceKind, setSourceKind] = useState(dataset?.source_kind ?? "manual");
  const [description, setDescription] = useState(dataset?.description ?? "");
  const [metadataJson, setMetadataJson] = useState(
    JSON.stringify(dataset?.metadata ?? {}, null, 2),
  );
  const [pending, setPending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      if (isEditing && !datasetId) {
        throw new Error("Dataset is unavailable.");
      }

      const payload = compactObject({
        name: name.trim(),
        source_kind: sourceKind.trim(),
        description: description.trim() || undefined,
        metadata: parseJsonRecord(metadataJson),
      });

      await requestJson(
        isEditing ? `/api/datasets/${datasetId}` : `/api/projects/${projectId}/datasets`,
        isEditing ? "PATCH" : "POST",
        payload,
      );

      setStatusMessage("Dataset saved. Refreshing the catalog.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Dataset save failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="stack-list" onSubmit={handleSubmit}>
      <div className="section-grid">
        <label className="stack-list span-6">
          <span className="muted-text">Dataset name</span>
          <input
            aria-label="Dataset name"
            className="input-field"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Operations review"
          />
        </label>
        <label className="stack-list span-6">
          <span className="muted-text">Source kind</span>
          <input
            aria-label="Source kind"
            className="input-field"
            value={sourceKind}
            onChange={(event) => setSourceKind(event.target.value)}
            placeholder="manual"
          />
        </label>
        <label className="stack-list span-12">
          <span className="muted-text">Dataset description</span>
          <textarea
            aria-label="Dataset description"
            className="input-field"
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label className="stack-list span-12">
          <span className="muted-text">Dataset metadata</span>
          <textarea
            aria-label="Dataset metadata"
            className="input-field"
            rows={4}
            value={metadataJson}
            onChange={(event) => setMetadataJson(event.target.value)}
          />
        </label>
      </div>
      <div className="button-row">
        <button className="button-primary" type="submit" disabled={pending}>
          {pending ? "Saving..." : isEditing ? "Update dataset" : "Create dataset"}
        </button>
      </div>
      {statusMessage ? (
        <p aria-live="polite" className="muted-text">
          {statusMessage}
        </p>
      ) : null}
      {errorMessage ? (
        <p aria-live="polite" className="muted-text">
          {errorMessage}
        </p>
      ) : null}
    </form>
  );
}

type SourceAssetMutationFormProps = {
  projectId: string;
  datasets: Dataset[];
  asset?: SourceAsset;
};

export function SourceAssetMutationForm({
  projectId,
  datasets,
  asset,
}: SourceAssetMutationFormProps) {
  const router = useRouter();
  const isEditing = Boolean(asset);
  const assetId = asset?.id;
  const [assetKind, setAssetKind] = useState<SourceAsset["asset_kind"]>(asset?.asset_kind ?? "image");
  const [datasetId, setDatasetId] = useState(asset?.dataset_id ?? "");
  const [uri, setUri] = useState(asset?.uri ?? "");
  const [storageKey, setStorageKey] = useState(asset?.storage_key ?? "");
  const [mimeType, setMimeType] = useState(asset?.mime_type ?? "");
  const [checksum, setChecksum] = useState(asset?.checksum ?? "");
  const [durationMs, setDurationMs] = useState(
    asset?.duration_ms === null || asset?.duration_ms === undefined ? "" : String(asset.duration_ms),
  );
  const [widthPx, setWidthPx] = useState(
    asset?.width_px === null || asset?.width_px === undefined ? "" : String(asset.width_px),
  );
  const [heightPx, setHeightPx] = useState(
    asset?.height_px === null || asset?.height_px === undefined ? "" : String(asset.height_px),
  );
  const [frameRate, setFrameRate] = useState(
    asset?.frame_rate === null || asset?.frame_rate === undefined ? "" : String(asset.frame_rate),
  );
  const [transcript, setTranscript] = useState(asset?.transcript ?? "");
  const [metadataJson, setMetadataJson] = useState(
    JSON.stringify(asset?.metadata ?? {}, null, 2),
  );
  const [pending, setPending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setStatusMessage(null);
    setErrorMessage(null);

    try {
      if (isEditing && !assetId) {
        throw new Error("Source asset is unavailable.");
      }

      if (!uri.trim() && !isEditing) {
        throw new Error("Asset URI is required.");
      }

      const payload = compactObject({
        asset_kind: assetKind,
        uri: uri.trim(),
        dataset_id: datasetId.trim() || undefined,
        storage_key: storageKey.trim() || undefined,
        mime_type: mimeType.trim() || undefined,
        checksum: checksum.trim() || undefined,
        duration_ms: toOptionalNumber(durationMs),
        width_px: toOptionalNumber(widthPx),
        height_px: toOptionalNumber(heightPx),
        frame_rate: toOptionalNumber(frameRate),
        transcript: transcript.trim() || undefined,
        metadata: parseJsonRecord(metadataJson),
      });

      await requestJson(
        isEditing ? `/api/source-assets/${assetId}` : `/api/projects/${projectId}/source-assets`,
        isEditing ? "PATCH" : "POST",
        payload,
      );

      setStatusMessage("Source asset saved. Refreshing the catalog.");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Source asset save failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="stack-list" onSubmit={handleSubmit}>
      <div className="section-grid">
        <label className="stack-list span-4">
          <span className="muted-text">Asset kind</span>
          <select
            aria-label="Asset kind"
            className="input-field"
            value={assetKind}
            onChange={(event) => setAssetKind(event.target.value as SourceAsset["asset_kind"])}
          >
            {["image", "audio", "video"].map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label className="stack-list span-8">
          <span className="muted-text">Asset URI</span>
          <input
            aria-label="Asset URI"
            className="input-field"
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="https://example.com/media/1.wav"
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Dataset</span>
          <select
            aria-label="Dataset"
            className="input-field"
            value={datasetId}
            onChange={(event) => setDatasetId(event.target.value)}
          >
            <option value="">Project-scoped / no dataset</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </option>
            ))}
          </select>
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Storage key</span>
          <input
            aria-label="Storage key"
            className="input-field"
            value={storageKey}
            onChange={(event) => setStorageKey(event.target.value)}
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">MIME type</span>
          <input
            aria-label="MIME type"
            className="input-field"
            value={mimeType}
            onChange={(event) => setMimeType(event.target.value)}
          />
        </label>
        <label className="stack-list span-4">
          <span className="muted-text">Checksum</span>
          <input
            aria-label="Checksum"
            className="input-field"
            value={checksum}
            onChange={(event) => setChecksum(event.target.value)}
          />
        </label>
        <label className="stack-list span-3">
          <span className="muted-text">Duration ms</span>
          <input
            aria-label="Duration ms"
            className="input-field"
            inputMode="numeric"
            type="number"
            value={durationMs}
            onChange={(event) => setDurationMs(event.target.value)}
          />
        </label>
        <label className="stack-list span-3">
          <span className="muted-text">Width px</span>
          <input
            aria-label="Width px"
            className="input-field"
            inputMode="numeric"
            type="number"
            value={widthPx}
            onChange={(event) => setWidthPx(event.target.value)}
          />
        </label>
        <label className="stack-list span-3">
          <span className="muted-text">Height px</span>
          <input
            aria-label="Height px"
            className="input-field"
            inputMode="numeric"
            type="number"
            value={heightPx}
            onChange={(event) => setHeightPx(event.target.value)}
          />
        </label>
        <label className="stack-list span-3">
          <span className="muted-text">Frame rate</span>
          <input
            aria-label="Frame rate"
            className="input-field"
            inputMode="numeric"
            type="number"
            value={frameRate}
            onChange={(event) => setFrameRate(event.target.value)}
          />
        </label>
        <label className="stack-list span-12">
          <span className="muted-text">Transcript</span>
          <textarea
            aria-label="Transcript"
            className="input-field"
            rows={3}
            value={transcript}
            onChange={(event) => setTranscript(event.target.value)}
          />
        </label>
        <label className="stack-list span-12">
          <span className="muted-text">Asset metadata</span>
          <textarea
            aria-label="Asset metadata"
            className="input-field"
            rows={4}
            value={metadataJson}
            onChange={(event) => setMetadataJson(event.target.value)}
          />
        </label>
      </div>
      <div className="button-row">
        <button className="button-primary" type="submit" disabled={pending}>
          {pending ? "Saving..." : isEditing ? "Update source asset" : "Register source asset"}
        </button>
      </div>
      {statusMessage ? (
        <p aria-live="polite" className="muted-text">
          {statusMessage}
        </p>
      ) : null}
      {errorMessage ? (
        <p aria-live="polite" className="muted-text">
          {errorMessage}
        </p>
      ) : null}
    </form>
  );
}
