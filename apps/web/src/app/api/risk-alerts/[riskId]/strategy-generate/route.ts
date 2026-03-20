import { NextRequest, NextResponse } from "next/server";

import {
  isControllerApiError,
  requestRiskStrategyGeneration,
  serializeControllerApiError,
} from "@/lib/controller-api";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ riskId: string }> },
) {
  const { riskId } = await params;
  const body = await request.json().catch(() => ({}));

  try {
    const result = await requestRiskStrategyGeneration(riskId, body, {
      requestHeaders: request.headers,
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
