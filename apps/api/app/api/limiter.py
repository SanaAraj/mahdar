from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings


def client_address(request: Request) -> str:
    forwarded = request.headers.get("x-mahdar-client-ip", "").strip()
    return forwarded or get_remote_address(request)


limiter = Limiter(key_func=client_address)


def configure_limiter(settings: Settings) -> Limiter:

    limiter.enabled = settings.rate_limit_enabled
    return limiter
