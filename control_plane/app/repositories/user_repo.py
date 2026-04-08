from sqlalchemy.orm import Session

from control_plane.app.models.membership import Membership
from control_plane.app.models.role import Role
from control_plane.app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def create_with_membership(self, user: User, role: Role, membership: Membership) -> User:
        self.db.add_all([role, user, membership])
        self.db.flush()
        return user

    def get_membership_role(self, user_id: str) -> tuple[Membership | None, Role | None]:
        membership = self.db.query(Membership).filter(Membership.user_id == user_id).first()
        if not membership:
            return None, None
        role = self.db.query(Role).filter(Role.id == membership.role_id).first()
        return membership, role
