import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

describe("ProjectRiskCaptureForm", () => {
  beforeEach(() => {
    refreshMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("posts a risk signal through the platform route and refreshes after success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            risk_signal: {
              id: "signal_1",
            },
          },
        }),
        {
          status: 202,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { ProjectRiskCaptureForm } = await import("./project-risk-capture-form");

    render(<ProjectRiskCaptureForm projectId="proj_1" />);

    fireEvent.change(screen.getByLabelText("Source kind"), {
      target: { value: "manual" },
    });
    fireEvent.change(screen.getByLabelText("Signal type"), {
      target: { value: "delivery_delay" },
    });
    fireEvent.change(screen.getByLabelText("Severity"), {
      target: { value: "82" },
    });
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Vendor delivery is late" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Shipment missed the expected window." },
    });
    fireEvent.change(screen.getByLabelText("Observed at"), {
      target: { value: "2026-03-20T10:00" },
    });
    fireEvent.change(screen.getByLabelText("Signal payload"), {
      target: { value: '{"source":"manual"}' },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save signal only" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/proj_1/risk-signals",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      source_kind: "manual",
      signal_type: "delivery_delay",
      severity: 82,
      title: "Vendor delivery is late",
      description: "Shipment missed the expected window.",
      signal_payload: { source: "manual" },
    });
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("posts a risk signal and analysis request through the platform route", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            workflow_run: { id: "run_1" },
          },
        }),
        {
          status: 202,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    vi.stubGlobal("fetch", fetchMock);

    const { ProjectRiskCaptureForm } = await import("./project-risk-capture-form");

    render(<ProjectRiskCaptureForm projectId="proj_1" />);

    fireEvent.change(screen.getByLabelText("Source kind"), {
      target: { value: "workflow" },
    });
    fireEvent.change(screen.getByLabelText("Signal type"), {
      target: { value: "quality_drop" },
    });
    fireEvent.change(screen.getByLabelText("Severity"), {
      target: { value: "75" },
    });
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Quality drift detected" },
    });
    fireEvent.change(screen.getByLabelText("Observed at"), {
      target: { value: "2026-03-20T11:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save and analyze" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/proj_1/risk-generate",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
  });
});
