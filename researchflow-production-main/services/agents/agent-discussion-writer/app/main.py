from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.run import router as run_router

app = FastAPI(title="ResearchFlow Agent Discussion Writer", version="0.1.0")

app.include_router(health_router)
app.include_router(run_router)
