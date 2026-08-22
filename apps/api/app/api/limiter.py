from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings

limiter = Limiter(key_func=get_remote_address)


def configure_limiter(settings: Settings) -> Limiter:

    limiter.enabled = settings.rate_limit_enabled
    return limiter
