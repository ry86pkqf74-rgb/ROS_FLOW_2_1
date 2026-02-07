from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.run import router as run_router

app = FastAPI(
    title="ResearchFlow Specialist Agent: Stage 2 Synthesize",
    version="0.1.0",
    description="Grounded literature review from extraction rows + citations; no claims without evidence.",
)
app.include_router(health_router)
app.include_router(run_router)
