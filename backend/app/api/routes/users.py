from fastapi import APIRouter, Depends, HTTPException, Response
from sqlite3 import IntegrityError
from app.api.dependencies import require_roles, record_audit
from app.db import database
from app.schemas.operations import UserCreate, UserUpdate
from app.services.auth_service import hash_password

router = APIRouter()


@router.get("/")
def get_users(user=Depends(require_roles("admin"))):
    return {"data": database.list_users()}


@router.post("/", status_code=201)
def create_user(payload: UserCreate, user=Depends(require_roles("admin"))):
    if payload.role == "brigade_operator" and not payload.brigade_id:
        raise HTTPException(422, "Asigna una brigada a cada Operador de Brigada.")
    if payload.brigade_id and not database.get_brigade(payload.brigade_id):
        raise HTTPException(404, "No existe esa brigada.")
    try:
        created = database.create_user(payload.username, payload.full_name, hash_password(payload.password), payload.role, payload.brigade_id)
    except IntegrityError:
        raise HTTPException(409, "Ese nombre de usuario ya está registrado.")
    record_audit(user, "Usuario creado", "usuario", created["id"], {"username": created["username"], "role": created["role"]})
    return {"id": created["id"], "username": created["username"], "full_name": created["full_name"],
            "role": created["role"], "brigade_id": created.get("brigade_id"), "active": created["active"]}


@router.patch("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, user=Depends(require_roles("admin"))):
    target = database.get_user(user_id)
    if not target: raise HTTPException(404, "No se encontró el usuario.")
    fields = payload.model_dump(exclude_unset=True)
    password = fields.pop("password", None)
    fields = {key: value for key,value in fields.items() if value is not None or key == "brigade_id"}
    if password: fields["password_hash"] = hash_password(password)
    if fields.get("brigade_id") and not database.get_brigade(fields["brigade_id"]):
        raise HTTPException(404, "No existe esa brigada.")
    new_role = fields.get("role", target["role"])
    new_active = fields.get("active", target["active"])
    if new_role == "brigade_operator" and fields.get("brigade_id", target.get("brigade_id")) is None:
        raise HTTPException(422, "Asigna una brigada a cada Operador de Brigada.")
    if target["role"] == "admin" and target["active"] and (new_role != "admin" or not new_active) and database.active_admin_count() <= 1:
        raise HTTPException(409, "No puedes desactivar o cambiar el único administrador activo.")
    updated = database.update_user(user_id, fields)
    record_audit(user, "Usuario actualizado", "usuario", user_id, {"fields": sorted(fields.keys())})
    return {"id": updated["id"], "username": updated["username"], "full_name": updated["full_name"],
            "role": updated["role"], "brigade_id": updated.get("brigade_id"), "active": updated["active"]}


@router.delete("/{user_id}", status_code=204)
def deactivate_user(user_id: int, user=Depends(require_roles("admin"))):
    target = database.get_user(user_id)
    if not target: raise HTTPException(404, "No se encontró el usuario.")
    if user_id == user["id"]: raise HTTPException(409, "No puedes desactivar tu propia cuenta.")
    if target["role"] == "admin" and target["active"] and database.active_admin_count() <= 1:
        raise HTTPException(409, "El sistema debe conservar al menos un administrador activo.")
    database.update_user(user_id, {"active": 0})
    record_audit(user, "Usuario desactivado", "usuario", user_id, {"username": target["username"]})
    return Response(status_code=204)
