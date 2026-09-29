from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.dependencies import current_user, require_roles, record_audit
from app.db import database
from app.schemas.operations import AssignmentCreate, AssignmentUpdate, DecisionCreate, IncidentUpdate, PolicyUpdate
from app.services.resource_service import suggest_brigades

router = APIRouter()


@router.get("/incidents")
def incidents(status: str | None = None, limit: int = Query(default=250, ge=1, le=1000), user=Depends(current_user)):
    rows = database.get_all_sensors_data(limit)
    if user["role"] == "reporter":
        rows = [row for row in rows if row.get("reporter_id") == user["id"]]
    if status:
        rows = [row for row in rows if row.get("resolution_status") == status]
    return {"data": rows, "total": len(rows)}


@router.patch("/incidents/{incident_id}")
def update_incident(incident_id: int, payload: IncidentUpdate, user=Depends(require_roles("admin", "coordinator"))):
    previous = database.get_incident(incident_id)
    if not previous: raise HTTPException(404, "No se encontró la alerta.")
    fields = payload.model_dump(exclude_unset=True)
    note = fields.pop("decision_note", "").strip()
    fields = {key: value for key, value in fields.items() if value is not None}
    if not fields: raise HTTPException(422, "Indica una prioridad, validación o estado que quieras actualizar.")
    updated = database.update_incident(incident_id, fields)
    changes = {key: {"anterior": previous.get(key), "nuevo": value} for key, value in fields.items() if previous.get(key) != value}
    details = note or "; ".join(f"{key}: {v['anterior']} → {v['nuevo']}" for key,v in changes.items())
    database.create_decision(incident_id, user["id"], "Actualización de alerta", details)
    record_audit(user, "Alerta actualizada", "incidente", incident_id, changes)
    return updated


@router.get("/incidents/{incident_id}/recommendations")
def incident_recommendations(incident_id: int, user=Depends(require_roles("admin", "coordinator"))):
    incident = database.get_incident(incident_id)
    if not incident: raise HTTPException(404, "No se encontró la alerta.")
    return {"incident_id": incident_id,
            "method": "Compatibilidad de capacidades y distancia geográfica directa.",
            "road_routes_available": False,
            "data_note": "La distancia no representa una ruta vial; coordinación confirma cada despacho.",
            "data": suggest_brigades(incident, database.list_brigades())}


@router.get("/assignments")
def assignments(user=Depends(require_roles("admin", "coordinator", "brigade_operator"))):
    rows = database.list_assignments()
    if user["role"] == "brigade_operator":
        rows = [row for row in rows if row["brigade_id"] == user.get("brigade_id")]
    return {"data": rows}


@router.post("/assignments", status_code=201)
def create_assignment(payload: AssignmentCreate, user=Depends(require_roles("admin", "coordinator"))):
    incident = database.get_incident(payload.incident_id)
    brigade = database.get_brigade(payload.brigade_id)
    if not incident: raise HTTPException(404, "No se encontró la alerta.")
    if not brigade: raise HTTPException(404, "No se encontró la brigada.")
    if incident["resolution_status"] in ("Resuelta", "Cancelada"):
        raise HTTPException(409, "No puedes asignar una alerta cerrada.")
    if brigade["status"] != "Disponible": raise HTTPException(409, "La brigada no está disponible.")
    if incident["triage_state"] != "Validada": raise HTTPException(409, "El coordinador debe validar la prioridad antes de asignar.")
    if any(a["incident_id"] == payload.incident_id and a["status"] in ("Asignada", "En camino", "Atendiendo")
           for a in database.list_assignments()):
        raise HTTPException(409, "Esta alerta ya tiene una brigada atendiendo la asignación.")
    assignment_id = database.create_assignment(payload.incident_id, payload.brigade_id, user["id"], payload.note)
    detail = payload.note.strip() or f"Asignación de {brigade['name']} a la alerta #{payload.incident_id}."
    database.create_decision(payload.incident_id, user["id"], "Brigada asignada", detail)
    record_audit(user, "Asignación creada", "asignación", assignment_id,
                 {"incident_id": payload.incident_id, "brigade_id": payload.brigade_id})
    return next((row for row in database.list_assignments() if row["id"] == assignment_id), None)


@router.patch("/assignments/{assignment_id}")
def update_assignment(assignment_id: int, payload: AssignmentUpdate, user=Depends(current_user)):
    assignment = database.get_assignment(assignment_id)
    if not assignment: raise HTTPException(404, "No se encontró la asignación.")
    allowed_transitions = {
        "Asignada": {"En camino", "Atendiendo", "Completada", "Cancelada"},
        "En camino": {"Atendiendo", "Completada", "Cancelada"},
        "Atendiendo": {"Completada", "Cancelada"},
        "Completada": set(),
        "Cancelada": set(),
    }
    if payload.status not in allowed_transitions.get(assignment["status"], set()):
        raise HTTPException(409, f"No se puede cambiar de {assignment['status']} a {payload.status}.")
    if user["role"] == "brigade_operator":
        if user.get("brigade_id") != assignment["brigade_id"]:
            raise HTTPException(403, "Esta asignación no corresponde a tu brigada.")
        if payload.status not in ("En camino", "Atendiendo", "Completada"):
            raise HTTPException(403, "El operador solo puede informar el avance o completar la atención.")
    elif user["role"] not in ("admin", "coordinator"):
        raise HTTPException(403, "Tu rol no permite actualizar asignaciones.")
    row = database.update_assignment(assignment_id, payload.status, payload.details)
    database.create_decision(assignment["incident_id"], user["id"], f"Asignación: {payload.status}", payload.details or "Estado operativo actualizado.")
    record_audit(user, "Asignación actualizada", "asignación", assignment_id, {"status": payload.status})
    return row


@router.get("/decisions")
def decisions(limit: int = Query(default=100, ge=1, le=500), user=Depends(require_roles("admin", "coordinator"))):
    return {"data": database.list_decisions(limit)}


@router.post("/decisions", status_code=201)
def create_decision(payload: DecisionCreate, user=Depends(require_roles("admin", "coordinator"))):
    if payload.incident_id and not database.get_incident(payload.incident_id):
        raise HTTPException(404, "No se encontró la alerta vinculada.")
    decision_id = database.create_decision(payload.incident_id, user["id"], payload.action, payload.details)
    record_audit(user, "Decisión registrada", "decisión", decision_id, {"action": payload.action, "incident_id": payload.incident_id})
    return {"id": decision_id, "incident_id": payload.incident_id, "action": payload.action, "details": payload.details}


@router.get("/policies")
def policies(user=Depends(require_roles("admin"))):
    return {"data": database.list_policies()}


@router.patch("/policies")
def update_policies(payload: PolicyUpdate, user=Depends(require_roles("admin"))):
    values = payload.model_dump(exclude_unset=True)
    values = {key: value for key,value in values.items() if value is not None}
    previous = database.list_policies()
    result = database.update_policies(values, user["id"])
    record_audit(user, "Políticas actualizadas", "política", None,
                 {key: {"anterior": previous.get(key), "nuevo": value} for key,value in values.items()})
    return {"data": result}


@router.get("/audit")
def audit_log(user=Depends(require_roles("admin"))):
    return {"data": database.list_audit()}
