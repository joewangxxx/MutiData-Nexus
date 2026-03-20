import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("RiskAlertActions", () => {
  beforeEach(() => {
    refreshMock.mockReset();
  });

  it("saves alert changes through the backend proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            risk_alert: {
              id: "alert_1",
              project_id: "proj_1",
              risk_signal_id: "signal_1",
              status: "open",
              severity: 70,
              title: "Supplier drift",
              summary: "Vendor delivery is late",
              assigned_to_user_id: "user_pm_1",
              detected_by_workflow_run_id: "run_1",
              next_review_at: "2026-03-21T10:00:00Z",
              resolved_at: null,
            },
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { RiskAlertActions } = await import("./risk-alert-actions");

    render(
      <RiskAlertActions
        alert={{
          id: "alert_1",
          project_id: "proj_1",
          risk_signal_id: "signal_1",
          status: "open",
          severity: 70,
          title: "Supplier drift",
          summary: "Vendor delivery is late",
          assigned_to_user_id: "user_pm_1",
          detected_by_workflow_run_id: "run_1",
          next_review_at: "2026-03-21T10:00:00Z",
          resolved_at: null,
        }}
        />,
    );

    expect(screen.getByLabelText("Status")).toBeInTheDocument();
    expect(screen.getByLabelText("Assigned to user id")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Updated supplier drift" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/risk-alerts/alert_1",
        expect.objectContaining({
          method: "PATCH",
        }),
      );
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("acknowledges open alerts through the backend proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            risk_alert: {
              id: "alert_1",
              project_id: "proj_1",
              risk_signal_id: "signal_1",
              status: "open",
              severity: 70,
              title: "Supplier drift",
              summary: "Vendor delivery is late",
              assigned_to_user_id: "user_pm_1",
              detected_by_workflow_run_id: "run_1",
              next_review_at: "2026-03-21T10:00:00Z",
              resolved_at: null,
            },
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { RiskAlertActions } = await import("./risk-alert-actions");

    render(
      <RiskAlertActions
        alert={{
          id: "alert_1",
          project_id: "proj_1",
          risk_signal_id: "signal_1",
          status: "open",
          severity: 70,
          title: "Supplier drift",
          summary: "Vendor delivery is late",
          assigned_to_user_id: "user_pm_1",
          detected_by_workflow_run_id: "run_1",
          next_review_at: "2026-03-21T10:00:00Z",
          resolved_at: null,
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Acknowledge alert" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/risk-alerts/alert_1/acknowledge",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
