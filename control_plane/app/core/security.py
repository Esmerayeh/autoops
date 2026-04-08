from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from control_plane.app.core.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(slots=True)
class Principal:
    subject: str
    tenant_id: str
    permissions: list[str]
    token_type: str


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_token(subject: str, tenant_id: str, permissions: list[str], token_type: str = "user") -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_exp_minutes)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "permissions": permissions,
        "token_type": token_type,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def decode_principal(token: str) -> Principal:
    payload = decode_token(token)
    return Principal(
        subject=payload["sub"],
        tenant_id=payload["tenant_id"],
        permissions=list(payload.get("permissions", [])),
        token_type=payload.get("token_type", "user"),
    )
