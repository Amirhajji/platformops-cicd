"""PlatformOPS API."""
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS

app = FastAPI(title="PlatformOPS API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    """Used by Jenkins and Blackbox. It must not touch the database."""
    return {"status": "ok"}
