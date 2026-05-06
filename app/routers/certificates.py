import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.device_auth import get_current_device
from app.config import get_settings
from app.database import get_db
from app.models.certificate import Certificate
from app.models.device import Device
from app.schemas.certificate import (
    CertificateRequestSchema,
    CertificateResponse,
    CertificateRenewSchema,
    CertificateRevokeSchema,
)
from app.services.certificate_service import get_ca

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


@router.post("/request", response_model=CertificateResponse, status_code=201)
async def request_certificate(
    data: CertificateRequestSchema,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    ca = get_ca()

    try:
        cert_pem, serial, issued_at, expires_at = ca.sign_csr(
            data.csr_pem, validity_days=settings.cert_validity_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from cryptography.x509 import load_pem_x509_csr
    from cryptography.x509.oid import NameOID
    csr = load_pem_x509_csr(data.csr_pem.encode())
    cn_attrs = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    common_name = cn_attrs[0].value if cn_attrs else device.name

    cert = Certificate(
        device_id=device.id,
        serial_number=serial,
        common_name=common_name,
        issued_at=issued_at,
        expires_at=expires_at,
        status="active",
        certificate_pem=cert_pem,
        csr_pem=data.csr_pem,
    )
    db.add(cert)
    await db.flush()
    await db.refresh(cert)
    return cert


@router.post("/renew", response_model=CertificateResponse, status_code=201)
async def renew_certificate(
    data: CertificateRenewSchema,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    ca = get_ca()

    q = select(Certificate).where(Certificate.device_id == device.id)
    if data.serial_number is not None:
        q = q.where(Certificate.serial_number == data.serial_number)
    elif data.certificate_id is not None:
        q = q.where(Certificate.id == data.certificate_id)
    else:
        q = q.where(Certificate.status == "active").order_by(Certificate.issued_at.desc())

    old = await db.scalar(q.limit(1))
    if not old:
        raise HTTPException(status_code=404, detail="Certificate not found")

    csr_pem = data.new_csr_pem or old.csr_pem
    if not csr_pem:
        raise HTTPException(status_code=400, detail="No CSR available; provide new_csr_pem")

    try:
        cert_pem, serial, issued_at, expires_at = ca.sign_csr(csr_pem, validity_days=settings.cert_validity_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    new_cert = Certificate(
        device_id=device.id,
        serial_number=serial,
        common_name=old.common_name,
        issued_at=issued_at,
        expires_at=expires_at,
        status="active",
        certificate_pem=cert_pem,
        csr_pem=csr_pem,
    )
    db.add(new_cert)
    await db.flush()
    await db.refresh(new_cert)
    return new_cert


@router.post("/revoke", status_code=200)
async def revoke_certificate(
    data: CertificateRevokeSchema,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    if data.serial_number is None and data.certificate_id is None:
        raise HTTPException(status_code=400, detail="Provide serial_number or certificate_id")

    q = select(Certificate).where(
        Certificate.device_id == device.id,
        Certificate.status == "active",
    )
    if data.serial_number is not None:
        q = q.where(Certificate.serial_number == data.serial_number)
    else:
        q = q.where(Certificate.id == data.certificate_id)

    cert = await db.scalar(q)
    if not cert:
        raise HTTPException(status_code=404, detail="Active certificate not found")

    cert.status = "revoked"
    cert.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    return {"status": "revoked", "serial_number": cert.serial_number}
