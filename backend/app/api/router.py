from fastapi import APIRouter
from app.api.routes import health, sensors

api_router = APIRouter()

# Incluimos las rutas
api_router.include_router(health.router, prefix="/health", tags=["Sistema"])
api_router.include_router(sensors.router, prefix="/sensors", tags=["Sensores ESP32"])