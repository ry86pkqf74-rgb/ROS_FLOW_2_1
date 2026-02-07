from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.run import router as run_router

app = FastAPI(
    title="ResearchFlow Specialist Agent: RAG Retrieve",
    version="0.1.0",
    description="Semantic search + BM25-lite reranking over ChromaDB collections",
)

app.include_router(health_router)
app.include_router(run_router)
