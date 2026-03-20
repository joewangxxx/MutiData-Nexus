import { describe, expect, it } from "vitest";
import { afterEach, beforeEach, vi } from "vitest";

describe("readyz route", () => {
  const originalControllerApiUrl = process.env.CONTROLLER_API_URL;

  beforeEach(() => {
    process.env.CONTROLLER_API_URL = "http://controller:8000";
  });

  afterEach(() => {
    process.env.CONTROLLER_API_URL = originalControllerApiUrl;
    vi.unstubAllGlobals();
  });

  it("returns a ready status payload when controller health is reachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ data: { status: "ok" } }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    const { GET } = await import("./route");

    const response = await GET();
    const payload = (await response.json()) as {
      status: string;
      checks: { controller: string };
      issues: string[];
    };

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      status: "ready",
      checks: { controller: "ok" },
      issues: [],
    });
  });

  it("returns a degraded payload when controller health is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));

    const { GET } = await import("./route");

    const response = await GET();
    const payload = (await response.json()) as {
      status: string;
      checks: { controller: string };
      issues: string[];
    };

    expect(response.status).toBe(503);
    expect(payload.status).toBe("degraded");
    expect(payload.checks.controller).toBe("failed");
    expect(payload.issues).toContain("Controller health check is unavailable.");
  });
});
