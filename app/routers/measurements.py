import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.device_auth import get_current_device, require_grafana_auth
from app.database import get_db
from app.models.device import Device
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementAck, MeasurementCreate, MeasurementResponse

router = APIRouter(prefix="/api/v1", tags=["measurements"])


@router.post("/measurements", response_model=MeasurementAck, status_code=201)
async def post_measurement(
    data: MeasurementCreate,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    m = Measurement(
        device_id=device.id,
        timestamp=data.timestamp,
        sensor_type=data.sensor_type,
        value=data.value,
        unit=data.unit,
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)
    return MeasurementAck(status="ok", measurement_id=m.id, timestamp=m.timestamp)


@router.get(
    "/measurements",
    response_model=list[MeasurementResponse],
    dependencies=[Depends(require_grafana_auth)],
)
async def get_measurements(
    device_id: uuid.UUID | None = Query(None),
    sensor_type: str | None = Query(None),
    from_time: datetime | None = Query(None),
    to_time: datetime | None = Query(None),
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Measurement).order_by(Measurement.timestamp.desc())

    if device_id:
        q = q.where(Measurement.device_id == device_id)
    if sensor_type:
        q = q.where(Measurement.sensor_type == sensor_type)
    if from_time:
        q = q.where(Measurement.timestamp >= from_time)
    if to_time:
        q = q.where(Measurement.timestamp <= to_time)

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
