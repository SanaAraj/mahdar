import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app import factory, strings
from app.api.deps import MessageError
from app.api.limiter import configure_limiter
from app.api.router import router
from app.config import Settings, get_settings
from app.features.diarization.diarize_local import LocalDiarizer
from app.pipeline.pipeline import Pipeline
from app.shared.errors import MahdarError
from app.shared.jobs import JobRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def _error_payload(message_key: str) -> dict[str, str]:
    return {"error_ar": strings.resolve(message_key), "code": message_key}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=strings.resolve("app.title"), docs_url=None, redoc_url=None)
    registry = JobRegistry(settings.data_dir)
    diarizer = LocalDiarizer(settings) if settings.hf_token else None
    factory.validate_providers(settings)
    app.state.settings = settings
    app.state.registry = registry
    app.state.pipeline = Pipeline(
        registry,
        factory.build_transcriber(settings),
        diarizer,
        factory.build_extractor(settings),
        max_active=settings.max_active_jobs,
    )
    _install_rate_limit(app, settings)
    _install_cors(app, settings)
    _install_handlers(app)
    app.include_router(router, prefix="/api")
    return app


def _install_rate_limit(app: FastAPI, settings: Settings) -> None:
    app.state.limiter = configure_limiter(settings)


def _install_cors(app: FastAPI, settings: Settings) -> None:

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["*"],
        )


def _install_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        body = _error_payload("rate.limited")
        body["detail"] = body["error_ar"]
        response = JSONResponse(status_code=429, content=body)
        response = request.app.state.limiter._inject_headers(response, exc)
        return response

    @app.exception_handler(MessageError)
    async def message_error_handler(request: Request, exc: MessageError) -> JSONResponse:
        body = _error_payload(exc.message_key)
        body["detail"] = body["error_ar"]
        response = JSONResponse(status_code=exc.status_code, content=body)
        if exc.message_key == "server.busy":
            response.headers["Retry-After"] = "30"
        return response

    @app.exception_handler(MahdarError)
    async def mahdar_error_handler(_request: Request, exc: MahdarError) -> JSONResponse:
        body = _error_payload(exc.message_key)
        body["detail"] = body["error_ar"]
        status = 413 if exc.message_key == "upload.file_too_large" else 422
        return JSONResponse(status_code=status, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        body = _error_payload("request.invalid")
        body["detail"] = body["error_ar"]
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def unexpected_handler(_request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unexpected API error")
        body = _error_payload("analysis.unexpected")
        body["detail"] = body["error_ar"]
        return JSONResponse(status_code=500, content=body)


_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:

    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    global _app
    if _app is None:
        _app = create_app()
    return _app
