from fastapi import APIRouter

router = APIRouter()

# Import and register v1 routes
from agenteval.api.v1 import health, workspaces, projects, datasets, scenarios, evaluations, judges, traces, reports, regressions, plugins

router.include_router(health.router, tags=["health"])
router.include_router(workspaces.router, tags=["workspaces"])
router.include_router(projects.router, tags=["projects"])
router.include_router(datasets.router, tags=["datasets"])
router.include_router(scenarios.router, tags=["scenarios"])
router.include_router(evaluations.router)
router.include_router(judges.router)
router.include_router(traces.router)
router.include_router(reports.router)
router.include_router(regressions.router)
router.include_router(plugins.router)
