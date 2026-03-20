import { describe, expect, it } from "vitest";

describe("healthz route", () => {
  it("returns an ok status payload", async () => {
    const { GET } = await import("./route");

    const response = await GET();
    const payload = (await response.json()) as { status: string };

    expect(response.status).toBe(200);
    expect(payload).toEqual({ status: "ok" });
  });
});
