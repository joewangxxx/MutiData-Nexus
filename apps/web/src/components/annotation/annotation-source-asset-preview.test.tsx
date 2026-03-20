import { render, screen } from "@testing-library/react";

describe("AnnotationSourceAssetPreview", () => {
  it("renders an image preview when the source asset is an image", async () => {
    const { AnnotationSourceAssetPreview } = await import("./annotation-source-asset-preview");

    render(
      <AnnotationSourceAssetPreview
        asset={{
          id: "asset_1",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          asset_kind: "image",
          uri: "https://example.com/assets/asset_1.jpg",
          storage_key: "assets/asset_1.jpg",
          mime_type: "image/jpeg",
          checksum: "sha256:asset_1",
          duration_ms: null,
          width_px: 1200,
          height_px: 800,
          frame_rate: null,
          transcript: null,
          metadata: {},
        }}
        access={{
          asset_id: "asset_1",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          asset_kind: "image",
          delivery_type: "direct_uri",
          uri: "https://signed.example.com/assets/asset_1.jpg",
          mime_type: "image/jpeg",
        }}
      />,
    );

    expect(screen.getByRole("img", { name: "Image preview for asset_1" })).toHaveAttribute(
      "src",
      "https://signed.example.com/assets/asset_1.jpg",
    );
    expect(screen.getByText("Unified media preview")).toBeInTheDocument();
  });

  it("renders audio and video controls when the source asset is media", async () => {
    const { AnnotationSourceAssetPreview } = await import("./annotation-source-asset-preview");

    const { rerender } = render(
      <AnnotationSourceAssetPreview
        asset={{
          id: "asset_2",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          asset_kind: "audio",
          uri: "https://example.com/assets/asset_2.mp3",
          storage_key: "assets/asset_2.mp3",
          mime_type: "audio/mpeg",
          checksum: "sha256:asset_2",
          duration_ms: 15000,
          width_px: null,
          height_px: null,
          frame_rate: null,
          transcript: "Voice note transcript",
          metadata: {},
        }}
        access={{
          asset_id: "asset_2",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          asset_kind: "audio",
          delivery_type: "direct_uri",
          uri: "https://signed.example.com/assets/asset_2.mp3",
          mime_type: "audio/mpeg",
        }}
      />,
    );

    expect(screen.getByText("Voice note transcript")).toBeInTheDocument();
    expect(screen.getByLabelText("Audio preview for asset_2")).toHaveAttribute(
      "src",
      "https://signed.example.com/assets/asset_2.mp3",
    );

    rerender(
      <AnnotationSourceAssetPreview
        asset={{
          id: "asset_3",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          asset_kind: "video",
          uri: "https://example.com/assets/asset_3.mp4",
          storage_key: "assets/asset_3.mp4",
          mime_type: "video/mp4",
          checksum: "sha256:asset_3",
          duration_ms: 30000,
          width_px: 1920,
          height_px: 1080,
          frame_rate: 30,
          transcript: null,
          metadata: {},
        }}
        access={{
          asset_id: "asset_3",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          asset_kind: "video",
          delivery_type: "direct_uri",
          uri: "https://signed.example.com/assets/asset_3.mp4",
          mime_type: "video/mp4",
        }}
      />,
    );

    expect(screen.getByLabelText("Video preview for asset_3")).toHaveAttribute(
      "src",
      "https://signed.example.com/assets/asset_3.mp4",
    );
  });
});
