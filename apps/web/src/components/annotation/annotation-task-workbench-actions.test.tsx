import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("AnnotationTaskWorkbenchActions", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("submits ai generate and revision actions through the live web routes", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            workflow_run: { id: "run_1" },
            coze_run: { id: "coze_1" },
            ai_result: { id: "ai_1" },
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            workflow_run: { id: "run_2" },
            coze_run: { id: "coze_2" },
            ai_result: { id: "ai_2" },
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    const { AnnotationTaskWorkbenchActions } = await import(
      "./annotation-task-workbench-actions"
    );

    render(
      <AnnotationTaskWorkbenchActions
        taskId="task_1"
        initialLabels={["label_a"]}
        initialContent="Seed content"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Generate AI suggestion" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/annotation-tasks/task_1/ai-generate",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    fireEvent.change(screen.getByLabelText("Labels"), {
      target: { value: "label_a, label_b" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Submitted from the workbench" },
    });
    fireEvent.change(screen.getByLabelText("Review notes"), {
      target: { value: "Ready for review" },
    });
    fireEvent.change(screen.getByLabelText("Confidence score"), {
      target: { value: "0.88" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit revision" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/annotation-tasks/task_1/submissions",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    const submissionRequest = fetchMock.mock.calls[1][1];
    expect(submissionRequest?.body).toBe(
      JSON.stringify({
        labels: ["label_a", "label_b"],
        content: { summary: "Submitted from the workbench" },
        review_notes: "Ready for review",
        confidence_score: 0.88,
      }),
    );
    expect(refreshMock).toHaveBeenCalledTimes(2);
  });
});
