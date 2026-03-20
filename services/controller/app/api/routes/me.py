from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_principal
from app.api.responses import success_response
from app.services.auth import CurrentPrincipal

router = APIRouter(tags=["identity"])


@router.get("/me")
def get_me(request: Request, principal: CurrentPrincipal = Depends(get_current_principal)) -> dict:
    return success_response(
        request,
        {
            "user": {
                "id": str(principal.user.id),
                "email": principal.user.email,
                "display_name": principal.user.display_name,
                "status": principal.user.status.value,
            },
            "organization": {
                "id": principal.organization_id,
                "slug": principal.organization_slug,
                "name": principal.organization_name,
                "status": principal.organization_status,
            },
            "organization_role": principal.organization_role,
            "project_memberships": [
                {
                    "project_id": membership.project_id,
                    "project_code": membership.project_code,
                    "project_name": membership.project_name,
                    "project_role": membership.project_role,
                    "status": membership.status,
                }
                for membership in principal.project_memberships
            ],
            "effective_permissions": sorted(principal.effective_permissions),
        },
    )
