from fastapi import APIRouter

from app.api.routes import candidates, employees, health, ops, payloads, results, screening

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(candidates.router)
api_router.include_router(employees.router)
api_router.include_router(payloads.router)
api_router.include_router(screening.router)
api_router.include_router(results.router)
api_router.include_router(ops.router)
