import { NextRequest, NextResponse } from "next/server";

import {
  isControllerApiError,
  serializeControllerApiError,
  updateAnnotationTask,
} from "@/lib/controller-api";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> },
) {
  const { taskId } = await params;
  const body = await request.json().catch(() => ({}));

  try {
    const result = await updateAnnotationTask(taskId, body, {
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
