import { NextRequest, NextResponse } from "next/server";

import {
  deleteProjectMember,
  isControllerApiError,
  serializeControllerApiError,
  updateProjectMember,
} from "@/lib/controller-api";

function buildIdempotencyKey(prefix: string): string {
  const randomId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`;
  return `${prefix}-${randomId}`;
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ projectId: string; membershipId: string }> },
) {
  const { projectId, membershipId } = await params;
  const body = await request.json().catch(() => ({}));

  try {
    const result = await updateProjectMember(
      projectId,
      membershipId,
      body,
      {
        requestHeaders: request.headers,
        idempotencyKey:
          request.headers.get("Idempotency-Key") ?? buildIdempotencyKey(`project-member-update-${membershipId}`),
      },
    );

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

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ projectId: string; membershipId: string }> },
) {
  const { projectId, membershipId } = await params;

  try {
    const result = await deleteProjectMember(projectId, membershipId, {
      requestHeaders: request.headers,
      idempotencyKey:
        request.headers.get("Idempotency-Key") ?? buildIdempotencyKey(`project-member-delete-${membershipId}`),
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
