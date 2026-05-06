import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.device_auth import generate_api_key, hash_api_key, require_admin_auth
from app.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceCreatedResponse, DeviceResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post(
    "/devices",
    response_model=DeviceCreatedResponse,
    status_code=201,
    dependencies=[Depends(require_admin_auth)],
)
async def register_device(data: DeviceCreate, db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(Device).where(Device.name == data.name)):
        raise HTTPException(status_code=409, detail="Device name already registered")

    api_key = generate_api_key()
    device = Device(name=data.name, api_key_hash=hash_api_key(api_key))
    db.add(device)
    await db.flush()
    await db.refresh(device)

    resp = DeviceCreatedResponse.model_validate(device)
    resp.api_key = api_key
    return resp


@router.get(
    "/devices",
    response_model=list[DeviceResponse],
    dependencies=[Depends(require_admin_auth)],
)
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).order_by(Device.created_at.desc()))
    return result.scalars().all()


@router.patch(
    "/devices/{device_id}/deactivate",
    status_code=200,
    dependencies=[Depends(require_admin_auth)],
)
async def deactivate_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    device = await db.scalar(select(Device).where(Device.id == device_id))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_active = False
    await db.flush()
    return {"status": "deactivated", "device_id": str(device_id)}
