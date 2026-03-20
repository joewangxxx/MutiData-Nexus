import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("AnnotationTaskManagementPanel", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("patches task management fields through the live web route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          task: { id: "task_1", status: "claimed" },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { AnnotationTaskManagementPanel } = await import(
      "./annotation-task-management-panel"
    );

    render(
      <AnnotationTaskManagementPanel
        task={{
          id: "task_1",
          project_id: "proj_1",
          dataset_id: "dataset_1",
          source_asset_id: "asset_1",
          task_type: "image_labeling",
          status: "queued",
          priority: 40,
          assigned_to_user_id: null,
          reviewer_user_id: null,
          created_by_user_id: "user_pm_1",
          current_workflow_run_id: null,
          latest_ai_result_id: null,
          annotation_schema: {},
          input_payload: {},
          output_payload: {},
          claimed_at: null,
          due_at: null,
          submitted_at: null,
          reviewed_at: null,
          completed_at: null,
        }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Priority"), {
      target: { value: "60" },
    });
    fireEvent.change(screen.getByLabelText("Due at"), {
      target: { value: "2026-03-20T09:15" },
    });
    fireEvent.change(screen.getByLabelText("Assignee"), {
      target: { value: "user_annotator_2" },
    });
    fireEvent.change(screen.getByLabelText("Reviewer"), {
      target: { value: "user_reviewer_2" },
    });
    fireEvent.change(screen.getByLabelText("Status"), {
      target: { value: "in_progress" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save task changes" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/annotation-tasks/task_1",
        expect.objectContaining({
          method: "PATCH",
        }),
      );
    });

    const requestBody = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(requestBody.priority).toBe(60);
    expect(requestBody.status).toBe("in_progress");
    expect(requestBody.assigned_to_user_id).toBe("user_annotator_2");
    expect(requestBody.reviewer_user_id).toBe("user_reviewer_2");
    expect(requestBody.due_at).toMatch(/T.*Z$/);
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
