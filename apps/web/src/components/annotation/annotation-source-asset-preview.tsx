/* eslint-disable @next/next/no-img-element */

import type { SourceAsset, SourceAssetAccess } from "@/lib/contracts";

import { KeyValueList, StatusBadge } from "@/components/ui/primitives";

type AnnotationSourceAssetPreviewProps = {
  asset: SourceAsset;
  access: SourceAssetAccess;
};

function buildFallbackLabel(asset: SourceAsset): string {
  const kindLabel = asset.asset_kind.charAt(0).toUpperCase() + asset.asset_kind.slice(1);
  return `${kindLabel} preview for ${asset.id}`;
}

export function AnnotationSourceAssetPreview({
  asset,
  access,
}: AnnotationSourceAssetPreviewProps) {
  const mediaLabel = buildFallbackLabel(asset);

  return (
    <div className="stack-list">
      <div className="notice tone-info">
        <h3>Unified media preview</h3>
        <p>Backend access envelope provided through the source-assets access path.</p>
      </div>

      {access.asset_kind === "image" ? (
        <img
          alt={mediaLabel}
          className="media-preview"
          src={access.uri}
        />
      ) : access.asset_kind === "audio" ? (
        <audio
          aria-label={mediaLabel}
          className="media-preview"
          controls
          src={access.uri}
        />
      ) : (
        <video
          aria-label={mediaLabel}
          className="media-preview"
          controls
          src={access.uri}
        />
      )}

      <KeyValueList
        items={[
          {
            label: "Asset kind",
            value: <StatusBadge value={asset.asset_kind} />,
          },
          {
            label: "Access delivery",
            value: access.delivery_type,
          },
          {
            label: "Access mime type",
            value: access.mime_type ?? asset.mime_type,
          },
        ]}
      />

      {asset.transcript ? (
        <div className="notice tone-info">
          <strong>Transcript</strong>
          <p>{asset.transcript}</p>
        </div>
      ) : null}
    </div>
  );
}
