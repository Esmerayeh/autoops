from pydantic import BaseModel, EmailStr


class TenantBootstrapRequest(BaseModel):
    tenant_name: str
    tenant_slug: str
    admin_email: EmailStr
    admin_password: str


class TenantBootstrapResponse(BaseModel):
    tenant_id: str
    admin_user_id: str
