from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterTenantRequest(BaseModel):
    organization: str
    slug: str
    industry: str = "construction"
    admin_name: str
    admin_email: EmailStr
    admin_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
