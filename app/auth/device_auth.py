import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.device import Device

_settings = get_settings()

_device_key_header = APIKeyHeader(name="X-Device-API-Key", auto_error=False)
_grafana_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_admin_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


def hash_api_key(api_key: str) -> str:
    return hmac.new(
        _settings.api_key_hmac_secret.encode(),
        api_key.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


async def get_current_device(
    api_key: str | None = Security(_device_key_header),
    db: AsyncSession = Depends(get_db),
) -> Device:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device API key required",
        )

    key_hash = hash_api_key(api_key)
    device = await db.scalar(
        select(Device).where(Device.api_key_hash == key_hash, Device.is_active == True)
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive device key",
        )

    device.last_seen_at = datetime.now(timezone.utc)
    await db.flush()
    return device


async def require_grafana_auth(
    api_key: str | None = Security(_grafana_key_header),
) -> None:
    if not api_key or not secrets.compare_digest(api_key, _settings.grafana_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Grafana API key required",
        )


async def require_admin_auth(
    api_key: str | None = Security(_admin_key_header),
) -> None:
    if not api_key or not secrets.compare_digest(api_key, _settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required",
        )
