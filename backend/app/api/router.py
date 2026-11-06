from fastapi import APIRouter
from .routes.health import router as health_router
from .routes.auth import router as auth_router
from .routes.admin import router as admin_router
from .routes.materials import router as materials_router
router = APIRouter(prefix='/api')
for feature_router in (health_router, auth_router, admin_router, materials_router):
    router.include_router(feature_router)
