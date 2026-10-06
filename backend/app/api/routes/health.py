from fastapi import APIRouter
from app.db.database import connection
from app.services.serial_service import serial_monitor

router = APIRouter()

@router.get("/")
async def health_check():
    db_ok = False
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    serial_ok = serial_monitor.serial_connection is not None and serial_monitor.serial_connection.is_open

    if not db_ok:
        return {"status": "error", "message": "Database not responding."}
    
    return {
        "status": "ok", 
        "message": "Centinela 503 API operando correctamente.",
        "database": "connected",
        "serial": "connected" if serial_ok else "disconnected"
    }
