from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterTenantRequest, TokenResponse
from app.services.common import save_model


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_tenant(payload: RegisterTenantRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.scalar(select(Tenant).where(Tenant.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Tenant slug already exists")
    tenant = save_model(db, Tenant(name=payload.organization, slug=payload.slug, industry=payload.industry), flush=True)
    user = User(
        tenant_id=tenant.id,
        email=str(payload.admin_email).lower(),
        full_name=payload.admin_name,
        hashed_password=hash_password(payload.admin_password),
        role=Role.OWNER.value,
    )
    save_model(db, user)
    return TokenResponse(access_token=create_access_token(user.id, tenant.id, user.role))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id, user.tenant_id, user.role))
