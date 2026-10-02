from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# El dashboard se sirve por separado en la misma máquina del piloto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    # Accept common local preview ports while keeping browser access loopback-only.
    allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)

# --- CONFIGURACIÓN PARA SERVIR EL FRONTEND DESDE FASTAPI ---
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.isdir(frontend_path):
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


docs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../documentacion/dist"))
if os.path.isdir(docs_path):
    app.mount("/documentacion", StaticFiles(directory=docs_path, html=True), name="documentacion")
