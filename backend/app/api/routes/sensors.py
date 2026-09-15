from fastapi import APIRouter
from app.db.database import get_all_sensors_data

router = APIRouter()

@router.get("/")
async def get_sensors():
    """
    Retorna todo el historial de alertas registradas por la Estación de Campo.
    """
    records = get_all_sensors_data()
    return {"total": len(records), "data": records}