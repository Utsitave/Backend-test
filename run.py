import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    ssl_kwargs: dict = {}
    if settings.tls_cert_path and settings.tls_key_path:
        ssl_kwargs = {
            "ssl_certfile": str(settings.tls_cert_path),
            "ssl_keyfile": str(settings.tls_key_path),
        }

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
        **ssl_kwargs,
    )
