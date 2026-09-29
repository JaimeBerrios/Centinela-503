from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from app.api.dependencies import current_user, record_audit
from app.db import database
from app.schemas.auth import BootstrapAdmin, LoginRequest
from app.services.auth_service import hash_password, issue_access_token, revoke_access_token, verify_password

router = APIRouter()
ROLE_LABELS = {
    "admin": "Administrador Institucional",
    "coordinator": "Coordinador de Emergencia",
    "brigade_operator": "Operador de Brigada",
    "reporter": "Reportante",
}


def public_user(user):
    return {key: user.get(key) for key in ("id", "username", "full_name", "role", "brigade_id", "active", "created_at")}


@router.get("/setup-status")
def setup_status():
    return {"setup_required": database.count_users() == 0}


@router.post("/setup", status_code=201)
def setup_admin(payload: BootstrapAdmin):
    if database.count_users() != 0:
        raise HTTPException(status_code=409, detail="La configuración inicial ya se completó.")
    user = database.create_user(payload.username, payload.full_name, hash_password(payload.password), "admin")
    token, expires = issue_access_token(user["id"])
    database.log_audit(user["id"], "Configuración inicial", "usuario", user["id"], {"username": user["username"]})
    return {"access_token": token, "token_type": "bearer", "expires_at": expires, "user": public_user(user)}


@router.post("/login")
def login(payload: LoginRequest):
    now = datetime.now(timezone.utc)
    since = (now - timedelta(minutes=15)).isoformat(timespec="seconds")
    if database.failed_login_count(payload.username, since) >= 5:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 15 minutos y vuelve a intentar.")
    user = database.get_user_by_username(payload.username)
    valid = bool(user and user["active"] and verify_password(payload.password, user["password_hash"]))
    database.log_login_attempt(payload.username, now.isoformat(timespec="seconds"), valid)
    if not valid:
        database.log_audit(None, "Inicio de sesión fallido", "autenticación", None,
                           {"username": payload.username.strip().lower()[:40]})
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    token, expires = issue_access_token(user["id"])
    database.log_audit(user["id"], "Inicio de sesión", "sesión", user["id"], {})
    return {"access_token": token, "token_type": "bearer", "expires_at": expires, "user": public_user(user)}


@router.get("/me")
def me(user=Depends(current_user)):
    result = public_user(user)
    result["role_label"] = ROLE_LABELS.get(user["role"], user["role"])
    return result


@router.post("/logout", status_code=204)
def logout(user=Depends(current_user), authorization: str | None = Header(default=None)):
    token = authorization.split(" ", 1)[1] if authorization and " " in authorization else ""
    if token:
        revoke_access_token(token)
    database.log_audit(user["id"], "Cierre de sesión", "sesión", user["id"], {})
    return Response(status_code=204)
