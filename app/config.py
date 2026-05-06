from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://iot_user:password@localhost:5432/iot_db"

    # Auth secrets
    grafana_api_key: str = "change_me"
    admin_api_key: str = "change_me"
    api_key_hmac_secret: str = "change_me_min_32_chars_secret_here_xx"

    # Certificate Authority
    ca_cert_path: Path = Path("certs/ca.crt")
    ca_key_path: Path = Path("certs/ca.key")
    ca_key_password: str | None = None
    ca_common_name: str = "IoT System CA"
    ca_org: str = "IoT System"
    cert_validity_days: int = 365

    # TLS (passed to uvicorn)
    tls_cert_path: Path | None = None
    tls_key_path: Path | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8443
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
