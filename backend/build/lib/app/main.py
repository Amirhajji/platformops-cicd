from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME
    }
