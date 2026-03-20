import { NextRequest, NextResponse } from "next/server";

import {
  isControllerApiError,
  registerProjectSourceAsset,
  serializeControllerApiError,
} from "@/lib/controller-api";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ projectId: string }> },
) {
  const { projectId } = await params;
  const body = await request.json().catch(() => ({}));

  try {
    const result = await registerProjectSourceAsset(projectId, body, {
      requestHeaders: request.headers,
    });

    return NextResponse.json(result, { status: 201 });
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
