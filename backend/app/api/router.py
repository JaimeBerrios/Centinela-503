from fastapi import APIRouter
from app.api.routes import auth, brigades, dashboard, health, operations, sensors, users

api_router = APIRouter()

# Incluimos las rutas
api_router.include_router(health.router, prefix="/health", tags=["Sistema"])
api_router.include_router(sensors.router, prefix="/sensors", tags=["Alertas y sensores"])
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación local"])
api_router.include_router(dashboard.router, tags=["Centro de operaciones"])
api_router.include_router(users.router, prefix="/users", tags=["Usuarios y roles"])
api_router.include_router(brigades.router, prefix="/brigades", tags=["Brigadas"])
api_router.include_router(operations.router, tags=["Asignaciones, decisiones y políticas"])
