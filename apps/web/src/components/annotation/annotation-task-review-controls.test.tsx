import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("AnnotationTaskReviewControls", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("defaults to the latest revision and posts reviewer decisions through the live web route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          review: {
            id: "review_3",
            annotation_task_id: "task_1",
            revision_id: "rev_1",
            reviewed_by_user_id: "user_reviewer_1",
            decision: "approve",
            notes: "Looks good",
            created_at: "2026-03-18T09:00:00Z",
          },
          task: {
            id: "task_1",
            status: "approved",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { AnnotationTaskReviewControls } = await import(
      "./annotation-task-review-controls"
    );

    render(
      <AnnotationTaskReviewControls
        taskId="task_1"
        revisions={[
          {
            id: "rev_2",
            annotation_task_id: "task_1",
            revision_no: 2,
            revision_kind: "submission",
            source_ai_result_id: null,
            created_by_user_id: "user_annotator_1",
            labels: ["label_b"],
            content: { summary: "Second draft" },
            review_notes: null,
            confidence_score: 0.9,
            created_at: "2026-03-18T08:30:00Z",
          },
          {
            id: "rev_1",
            annotation_task_id: "task_1",
            revision_no: 1,
            revision_kind: "submission",
            source_ai_result_id: null,
            created_by_user_id: "user_annotator_1",
            labels: ["label_a"],
            content: { summary: "First draft" },
            review_notes: null,
            confidence_score: 0.85,
            created_at: "2026-03-18T08:00:00Z",
          },
        ]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Review notes"), {
      target: { value: "Looks good" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/annotation-tasks/task_1/reviews",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(fetchMock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        revision_id: "rev_2",
        decision: "approve",
        notes: "Looks good",
      }),
    );
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
