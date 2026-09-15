import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Centinela 503 API"
    VERSION: str = "0.1.0"
    
    # Configuración Serial
    SERIAL_PORT: str = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
    SERIAL_BAUDRATE: int = int(os.getenv("SERIAL_BAUDRATE", 115200))
    SERIAL_TIMEOUT: int = int(os.getenv("SERIAL_TIMEOUT", 1))
    
    # Configuración de Base de Datos y ML
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/centinela.db")
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./app/ml/artifacts/model.pkl")

settings = Settings()