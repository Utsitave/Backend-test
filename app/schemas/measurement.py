import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MeasurementCreate(BaseModel):
    timestamp: datetime
    sensor_type: str = Field(..., min_length=1, max_length=100)
    value: float
    unit: str = Field(..., min_length=1, max_length=50)
    extra_data: dict[str, Any] | None = None


class MeasurementResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_id: uuid.UUID
    timestamp: datetime
    sensor_type: str
    value: float
    unit: str
    extra_data: dict[str, Any] | None = None
    created_at: datetime


class MeasurementAck(BaseModel):
    status: str = "ok"
    measurement_id: uuid.UUID
    timestamp: datetime
