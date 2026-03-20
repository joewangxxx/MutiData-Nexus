import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("AnnotationTaskQueueClaimButton", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("claims a queued task through the live web route", async () => {
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

    const { AnnotationTaskQueueClaimButton } = await import(
      "./annotation-task-queue-claim-button"
    );

    render(<AnnotationTaskQueueClaimButton taskId="task_1" claimable />);

    fireEvent.click(screen.getByRole("button", { name: "Claim task" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/annotation-tasks/task_1/claim",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
