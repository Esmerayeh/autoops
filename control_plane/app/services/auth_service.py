from datetime import UTC, datetime, timedelta
import uuid

from sqlalchemy.orm import Session

from control_plane.app.core.config import settings
from control_plane.app.core.security import create_token, hash_password, verify_password
from control_plane.app.models.membership import Membership
from control_plane.app.models.role import Role
from control_plane.app.models.user import User
from control_plane.app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate(self, email: str, password: str) -> dict | None:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None

        membership, role = self.user_repo.get_membership_role(user.id)
        if membership:
            permissions = list((role.permissions or {}).get("grants", [])) if role else []
            tenant_id = membership.tenant_id
        else:
            permissions = ["*"] if user.is_platform_admin else []
            tenant_id = "platform"

        return {
            "access_token": create_token(user.id, tenant_id, permissions),
            "expires_in": settings.jwt_exp_minutes * 60,
        }

    def create_user(self, email: str, password: str, tenant_id: str, permissions: list[str]) -> User:
        role = Role(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="owner",
            permissions={"grants": permissions},
        )
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        membership = Membership(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user.id,
            role_id=role.id,
        )
        self.user_repo.create_with_membership(user, role, membership)
        self.db.commit()
        return user
