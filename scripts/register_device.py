"""Register a new IoT device and print its one-time API key."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.models  # noqa: F401 — registers ORM models
from app.config import get_settings
from app.database import AsyncSessionLocal, Base, engine
from app.models.device import Device
from app.auth.device_auth import generate_api_key, hash_api_key


async def register(name: str) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api_key = generate_api_key()

    async with AsyncSessionLocal() as session:
        device = Device(name=name, api_key_hash=hash_api_key(api_key))
        session.add(device)
        await session.commit()
        await session.refresh(device)

    print(f"Device   : {device.name}")
    print(f"ID       : {device.id}")
    print(f"API Key  : {api_key}")
    print("Save this key — it cannot be recovered.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/register_device.py <device_name>")
        sys.exit(1)

    get_settings()  # fail fast on missing config
    asyncio.run(register(sys.argv[1]))
