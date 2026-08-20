import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app import strings
from backend.app.api.routes import MessageError, router
from backend.app.config import REPO_ROOT, get_settings
from backend.app.core.errors import MahdarError
from backend.app.core.jobs import JobRegistry
from backend.app.core.pipeline import Pipeline
from backend.app.providers import factory
from backend.app.providers.diarize_local import LocalDiarizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def _error_payload(message_key: str) -> dict[str, str]:
    return {"error_ar": strings.resolve(message_key), "code": message_key}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=strings.resolve("app.title"), docs_url=None, redoc_url=None)
    registry = JobRegistry(settings.data_dir)
    diarizer = LocalDiarizer(settings) if settings.hf_token else None
    factory._validate_providers(settings)
    app.state.settings = settings
    app.state.registry = registry
    app.state.pipeline = Pipeline(
        registry, factory.build_transcriber(settings), diarizer, factory.build_extractor(settings)
    )
    _install_handlers(app)
    app.include_router(router, prefix="/api")

    # Static frontend: a single-page ES-module app with no import hashes means a
    # stale browser cache can mix old and new modules (and get `undefined` on the
    # page). No-cache forces ETag revalidation each load, so a fresh build is
    # always picked up; unchanged files come back cheap 304s.
    class NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):
            response = await super().get_response(path, scope)
            response.headers["Cache-Control"] = "no-cache"
            return response

    app.mount("/", NoCacheStaticFiles(directory=REPO_ROOT / "frontend", html=True), name="frontend")
    return app


def _install_handlers(app: FastAPI) -> None:
    @app.exception_handler(MessageError)
    async def message_error_handler(_request: Request, exc: MessageError) -> JSONResponse:
        body = _error_payload(exc.message_key)
        body["detail"] = body["error_ar"]  # legacy clients still read detail
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(MahdarError)
    async def mahdar_error_handler(_request: Request, exc: MahdarError) -> JSONResponse:
        body = _error_payload(exc.message_key)
        body["detail"] = body["error_ar"]
        status = 413 if exc.message_key == "upload.file_too_large" else 422
        return JSONResponse(status_code=status, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        body = _error_payload("speaker.bad_body")
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
    # Create the app on first real access so importing the module never reads
    # the environment or the disk.
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    global _app
    if _app is None:
        _app = create_app()
    return _app
