from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import current_user, require_roles, record_audit
from app.db import database
from app.schemas.operations import BrigadeCreate, BrigadeUpdate

router = APIRouter()


@router.get("/")
def get_brigades(user=Depends(require_roles("admin", "coordinator", "brigade_operator"))):
    return {"data": database.list_brigades()}


@router.post("/", status_code=201)
def create_brigade(payload: BrigadeCreate, user=Depends(require_roles("admin"))):
    brigade = database.create_brigade(payload.name, payload.zone, payload.skills, payload.latitude, payload.longitude)
    record_audit(user, "Brigada creada", "brigada", brigade["id"], {"name": brigade["name"]})
    return brigade


@router.patch("/{brigade_id}")
def update_brigade(brigade_id: int, payload: BrigadeUpdate, user=Depends(current_user)):
    brigade = database.get_brigade(brigade_id)
    if not brigade: raise HTTPException(404, "No se encontró la brigada.")
    fields = payload.model_dump(exclude_unset=True)
    if user["role"] == "brigade_operator":
        if user.get("brigade_id") != brigade_id:
            raise HTTPException(403, "Solo puedes actualizar el estado de tu brigada.")
        if set(fields) != {"status"} or fields["status"] not in ("Disponible", "Fuera de servicio"):
            raise HTTPException(403, "El operador solo puede cambiar disponibilidad o reportarse fuera de servicio.")
        if fields["status"] == "Disponible" and any(
            a["brigade_id"] == brigade_id and a["status"] in ("Asignada", "En camino", "Atendiendo")
            for a in database.list_assignments()
        ):
            raise HTTPException(409, "Completa la asignación activa antes de volver a disponibilidad.")
    elif user["role"] not in ("admin", "coordinator"):
        raise HTTPException(403, "Tu rol no permite modificar brigadas.")
    fields = {key: value for key,value in fields.items() if value is not None or key in ("latitude", "longitude")}
    if fields.get("status") == "Disponible" and any(
        a["brigade_id"] == brigade_id and a["status"] in ("Asignada", "En camino", "Atendiendo")
        for a in database.list_assignments()
    ):
        raise HTTPException(409, "La brigada tiene una asignación activa.")
    result = database.update_brigade(brigade_id, fields)
    record_audit(user, "Brigada actualizada", "brigada", brigade_id, fields)
    return result
