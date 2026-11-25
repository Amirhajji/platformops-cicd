"""Every /api route. Only POST /api/auth/login works without a token."""
from fastapi import APIRouter, Depends

from app.api import auth, detections, metrics, scores, users
from app.api.deps import current_user

router = APIRouter(prefix="/api")
router.include_router(auth.router)
for protected in (scores.router, metrics.router, detections.router, users.router):
    router.include_router(protected, dependencies=[Depends(current_user)])
