import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CertificateRequestSchema(BaseModel):
    csr_pem: str = Field(..., description="PEM-encoded Certificate Signing Request")


class CertificateRenewSchema(BaseModel):
    serial_number: int | None = None
    certificate_id: uuid.UUID | None = None
    new_csr_pem: str | None = None


class CertificateRevokeSchema(BaseModel):
    serial_number: int | None = None
    certificate_id: uuid.UUID | None = None


class CertificateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_id: uuid.UUID
    serial_number: int
    common_name: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    status: str
    certificate_pem: str
