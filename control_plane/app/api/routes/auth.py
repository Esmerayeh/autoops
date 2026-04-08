from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from control_plane.app.api.deps import db_session
from control_plane.app.schemas.auth import LoginRequest, TokenResponse
from control_plane.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> TokenResponse:
    auth_service = AuthService(db)
    result = auth_service.authenticate(payload.email, payload.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(**result)
