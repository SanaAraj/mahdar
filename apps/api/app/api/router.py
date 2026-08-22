from fastapi import APIRouter

from app.features.analysis.routes import router as analysis_router
from app.features.export.routes import router as export_router
from app.features.meetings.routes import router as meetings_router

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(meetings_router)
router.include_router(analysis_router)
router.include_router(export_router)
