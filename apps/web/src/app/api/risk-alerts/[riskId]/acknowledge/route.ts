import { NextRequest, NextResponse } from "next/server";

import {
  acknowledgeRiskAlert,
  isControllerApiError,
  serializeControllerApiError,
} from "@/lib/controller-api";

function createIdempotencyKey(prefix: string): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`;
  return `${prefix}-${randomId}`;
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ riskId: string }> },
) {
  const { riskId } = await params;
  const idempotencyKey =
    request.headers.get("Idempotency-Key") ??
    createIdempotencyKey(`risk-alert-acknowledge-${riskId}`);

  try {
    const result = await acknowledgeRiskAlert(riskId, {
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
