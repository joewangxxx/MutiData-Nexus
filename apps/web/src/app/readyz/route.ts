import { NextResponse } from "next/server";

const DEFAULT_CONTROLLER_URL = "http://127.0.0.1:8000";

export async function GET() {
  const controllerBaseUrl =
    process.env.CONTROLLER_API_URL ??
    process.env.NEXT_PUBLIC_CONTROLLER_API_URL ??
    DEFAULT_CONTROLLER_URL;

  try {
    const response = await fetch(new URL("/api/v1/ops/healthz", controllerBaseUrl), {
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        {
          status: "degraded",
          checks: {
            controller: "failed",
          },
          issues: [`Controller health check returned status ${response.status}.`],
        },
        { status: 503 },
      );
    }
  } catch {
    return NextResponse.json(
      {
        status: "degraded",
        checks: {
          controller: "failed",
        },
        issues: ["Controller health check is unavailable."],
      },
      { status: 503 },
    );
  }

  return NextResponse.json({
    status: "ready",
    checks: {
      controller: "ok",
    },
    issues: [],
  });
}
