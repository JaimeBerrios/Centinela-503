from fastapi import APIRouter, Depends
from app.api.dependencies import require_roles, record_audit
from app.db.database import get_all_sensors_data, insert_sensor_data
from app.schemas.sensor import IncidentCreate
from app.services.prediction_service import suggest_triage
from app.db import database
from app.services.spatial_service import group_alerts

router = APIRouter()


@router.post("/", status_code=201)
async def create_incident(payload: IncidentCreate, user=Depends(require_roles("admin", "coordinator", "reporter"))):
    """Registra una alerta local enviada desde el dashboard."""
    suggestion = suggest_triage(payload.incident_text, payload.status)
    incident_id = insert_sensor_data(
        payload.node_id,
        payload.status,
        "Pendiente",
        payload.latitude,
        payload.longitude,
        payload.incident_text,
        category=suggestion["category"],
        suggested_priority=suggestion["suggested_priority"],
        suggested_reason=suggestion["basis"],
        triage_state="Pendiente de validación",
        source="dashboard",
        reporter_id=user["id"],
    )
    record = database.get_incident(incident_id)
    return {
        **record,
        "triage_basis": suggestion["basis"],
        "message": "Alerta registrada en el servidor local.",
    }

@router.get("/")
async def get_sensors(user=Depends(require_roles("admin", "coordinator", "brigade_operator", "reporter"))):
    """
    Retorna todo el historial de alertas, agrupadas automáticamente por 
    proximidad espacial (50 metros) para no saturar el mapa del frontend.
    """
    # 1. Obtenemos los datos crudos de SQLite
    raw_records = get_all_sensors_data()
    if user["role"] == "reporter":
        raw_records = [record for record in raw_records if record.get("reporter_id") == user["id"]]
    
    # 2. Pasamos los datos por nuestro algoritmo agrupador
    policies = database.list_policies()
    try: distance = max(10.0, min(500.0, float(policies.get("cluster_radius_m", "50"))))
    except (TypeError, ValueError): distance = 50.0
    grouped_clusters = group_alerts(raw_records, distance_threshold=distance)
    
    return {
        "total_raw_alerts": len(raw_records),
        "total_clusters": len(grouped_clusters),
        "data": grouped_clusters
    }
