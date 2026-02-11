# app/main.py
from fastapi import FastAPI
from app.api.routers import signals
from app.api import alerts, components, timeseries , propagation , auth , users
from app.api import analytics
from app.api import system, patterns, simulator
from app.api import anomalies
from fastapi.middleware.cors import CORSMiddleware
from app.api import incidents
from fastapi import status











app = FastAPI(title="PlatformOPS Observability API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173" ,"http://localhost:3000",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "ok Lionel messi"}

app.include_router(timeseries.router)
app.include_router(signals.router)
app.include_router(propagation.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(system.router)
app.include_router(patterns.router)
app.include_router(simulator.router)
app.include_router(anomalies.router)
app.include_router(incidents.router)
app.include_router(components.router)







