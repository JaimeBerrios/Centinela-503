from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.db import database
from app.services.auth_service import resolve_access_token

bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inicia sesión para continuar.")
    user = resolve_access_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión vencida o inválida.")
    return user


def require_roles(*roles):
    def check(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tu rol no permite esta acción.")
        return user
    return check


def record_audit(user, action: str, entity: str, entity_id=None, details=None):
    database.log_audit(user["id"], action, entity, entity_id, details or {})
