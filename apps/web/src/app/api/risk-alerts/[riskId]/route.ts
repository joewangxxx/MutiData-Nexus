import { NextRequest, NextResponse } from "next/server";

import {
  isControllerApiError,
  patchRiskAlert,
  serializeControllerApiError,
} from "@/lib/controller-api";

function createIdempotencyKey(prefix: string): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`;
  return `${prefix}-${randomId}`;
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ riskId: string }> },
) {
  const { riskId } = await params;
  const body = await request.json().catch(() => ({}));
  const idempotencyKey =
    request.headers.get("Idempotency-Key") ?? createIdempotencyKey(`risk-alert-patch-${riskId}`);

  try {
    const result = await patchRiskAlert(riskId, body, {
      requestHeaders: request.headers,
      idempotencyKey,
    });

    return NextResponse.json(result);
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
