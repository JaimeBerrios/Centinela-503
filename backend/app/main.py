from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api.router import api_router
from app.db.database import init_db
from app.services.serial_service import serial_monitor  # <--- Nuevo Import

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eventos de inicio
    print("Inicializando base de datos SQLite...")
    init_db()
    print("Arrancando monitor del puerto serial...")
    serial_monitor.start()  # <--- Iniciamos el monitor en segundo plano
    
    yield
    
    # Eventos de apagado
    print("Apagando monitor serial...")
    serial_monitor.stop()  # <--- Apagado seguro al detener el servidor

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API REST para el sistema de alertas LoRa - Centinela 503",
    lifespan=lifespan
)

app.include_router(api_router)