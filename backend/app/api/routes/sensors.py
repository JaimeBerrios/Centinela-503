from fastapi import APIRouter
from app.db.database import get_all_sensors_data
from app.services.spatial_service import group_alerts

router = APIRouter()

@router.get("/")
async def get_sensors():
    """
    Retorna todo el historial de alertas, agrupadas automáticamente por 
    proximidad espacial (50 metros) para no saturar el mapa del frontend.
    """
    # 1. Obtenemos los datos crudos de SQLite
    raw_records = get_all_sensors_data()
    
    # 2. Pasamos los datos por nuestro algoritmo agrupador
    grouped_clusters = group_alerts(raw_records, distance_threshold=50.0)
    
    return {
        "total_raw_alerts": len(raw_records),
        "total_clusters": len(grouped_clusters),
        "data": grouped_clusters
    }