from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.device_auth import require_grafana_auth
from app.database import get_db
from app.models.certificate import Certificate
from app.models.device import Device
from app.models.measurement import Measurement

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics", dependencies=[Depends(require_grafana_auth)])
async def get_metrics(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)

    total_devices = await db.scalar(select(func.count()).select_from(Device))
    active_devices = await db.scalar(
        select(func.count()).select_from(Device).where(Device.is_active == True)
    )
    total_measurements = await db.scalar(select(func.count()).select_from(Measurement))
    measurements_last_hour = await db.scalar(
        select(func.count()).select_from(Measurement)
        .where(Measurement.timestamp >= now - timedelta(hours=1))
    )
    measurements_last_day = await db.scalar(
        select(func.count()).select_from(Measurement)
        .where(Measurement.timestamp >= now - timedelta(hours=24))
    )
    active_certs = await db.scalar(
        select(func.count()).select_from(Certificate).where(Certificate.status == "active")
    )
    expiring_soon = await db.scalar(
        select(func.count()).select_from(Certificate).where(
            Certificate.status == "active",
            Certificate.expires_at <= now + timedelta(days=30),
        )
    )

    return {
        "timestamp": now.isoformat(),
        "devices": {"total": total_devices, "active": active_devices},
        "measurements": {
            "total": total_measurements,
            "last_hour": measurements_last_hour,
            "last_day": measurements_last_day,
        },
        "certificates": {
            "active": active_certs,
            "expiring_soon_30d": expiring_soon,
        },
    }
