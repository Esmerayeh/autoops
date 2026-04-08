from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from control_plane.app.core.db import get_db
from control_plane.app.core.security import Principal, decode_principal


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_current_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Resolve the current API principal from a bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_principal(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc


def require_permission(permission: str):
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        permissions = set(principal.permissions)
        if "*" in permissions or permission in permissions:
            return principal
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return dependency


def require_token_type(token_type: str):
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.token_type != token_type:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{token_type.title()} token required")
        return principal

    return dependency


def tenant_scope(principal: Principal = Depends(get_current_principal)) -> str:
    tenant_id = principal.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant scope missing")
    return tenant_id
