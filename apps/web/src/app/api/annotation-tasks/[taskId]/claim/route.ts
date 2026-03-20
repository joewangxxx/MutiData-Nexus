import { NextRequest, NextResponse } from "next/server";

import {
  claimAnnotationTask,
  isControllerApiError,
  serializeControllerApiError,
} from "@/lib/controller-api";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;

  try {
    const result = await claimAnnotationTask(taskId, {
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
