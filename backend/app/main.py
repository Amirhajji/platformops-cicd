"""PlatformOPS API (docs/API_V1.md)."""
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import CORS_ORIGINS
from app.core.errors import add_error_handlers

app = FastAPI(title="PlatformOPS API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_error_handlers(app)
app.include_router(router)


@app.get("/health")
def health() -> Dict[str, str]:
    """Used by Jenkins and Blackbox. It must not touch the database."""
    return {"status": "ok"}
