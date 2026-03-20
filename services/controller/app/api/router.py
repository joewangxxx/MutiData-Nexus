from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.annotation_tasks import router as annotation_tasks_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.me import router as me_router
from app.api.routes.projects import router as projects_router
from app.api.routes.ops import router as ops_router
from app.api.routes.risk import router as risk_router
from app.api.routes.source_assets import router as source_assets_router
from app.api.routes.workflow_runs import router as workflow_runs_router

api_router = APIRouter()
api_router.include_router(me_router)
api_router.include_router(ops_router)
api_router.include_router(projects_router)
api_router.include_router(datasets_router)
api_router.include_router(risk_router)
api_router.include_router(source_assets_router)
api_router.include_router(annotation_tasks_router)
api_router.include_router(workflow_runs_router)
api_router.include_router(integrations_router)
