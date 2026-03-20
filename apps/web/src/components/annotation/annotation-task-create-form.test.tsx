import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("AnnotationTaskCreateForm", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("creates a task through the live web route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          task: { id: "task_2", status: "queued" },
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { AnnotationTaskCreateForm } = await import("./annotation-task-create-form");

    render(
      <AnnotationTaskCreateForm
        projectId="proj_1"
        sourceAssets={[
          {
            id: "asset_1",
            project_id: "proj_1",
            dataset_id: "dataset_1",
            asset_kind: "image",
            uri: "https://example.com/asset_1.jpg",
            storage_key: "asset_1.jpg",
            mime_type: "image/jpeg",
            checksum: "sha256:asset1",
            duration_ms: null,
            width_px: 1200,
            height_px: 800,
            frame_rate: null,
            transcript: null,
            metadata: {},
          },
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Task type"), {
      target: { value: "image_labeling" },
    });
    fireEvent.change(screen.getByLabelText("Priority"), {
      target: { value: "80" },
    });
    fireEvent.change(screen.getByLabelText("Assignee"), {
      target: { value: "user_annotator_1" },
    });
    fireEvent.change(screen.getByLabelText("Reviewer"), {
      target: { value: "user_reviewer_1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create task" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/proj_1/annotation-tasks",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(fetchMock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        source_asset_id: "asset_1",
        task_type: "image_labeling",
        priority: 80,
        assigned_to_user_id: "user_annotator_1",
        reviewer_user_id: "user_reviewer_1",
      }),
    );
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
