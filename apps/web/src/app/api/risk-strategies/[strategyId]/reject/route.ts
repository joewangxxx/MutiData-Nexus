import { NextRequest, NextResponse } from "next/server";

import {
  isControllerApiError,
  requestRiskStrategyDecision,
  serializeControllerApiError,
} from "@/lib/controller-api";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ strategyId: string }> },
) {
  const { strategyId } = await params;
  const body = await request.json().catch(() => ({}));

  try {
    const result = await requestRiskStrategyDecision(strategyId, "reject", body, {
      requestHeaders: request.headers,
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
