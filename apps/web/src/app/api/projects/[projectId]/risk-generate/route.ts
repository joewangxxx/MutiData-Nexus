import { NextRequest, NextResponse } from "next/server";

import {
  isControllerApiError,
  requestProjectRiskGeneration,
  serializeControllerApiError,
} from "@/lib/controller-api";

function createIdempotencyKey(prefix: string): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`;
  return `${prefix}-${randomId}`;
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const body = await request.json().catch(() => ({}));
  const idempotencyKey =
    request.headers.get("Idempotency-Key") ?? createIdempotencyKey(`risk-generate-${projectId}`);

  try {
    const result = await requestProjectRiskGeneration(projectId, body, {
      requestHeaders: request.headers,
      idempotencyKey,
    });

    return NextResponse.json(result, { status: 202 });
  } catch (error) {
    const payload = serializeControllerApiError(error);
    if (payload) {
      return NextResponse.json(payload, {
        status: isControllerApiError(error) ? error.status : 500,
      });
    }

    throw error;
  }
}
