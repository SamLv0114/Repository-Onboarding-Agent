"""FastAPI app entrypoint. Start: uvicorn app.main:app --reload --reload-dir app.

Watch only app/: cloned repositories under data/ contain .py files that would
otherwise trigger a reload and kill running onboarding jobs.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import benchmarks, health, qa, repositories

app = FastAPI(
    title="Repository Onboarding Agent API",
    version="0.1.0",
    description="Development scaffold for the AMS 691 Repository Onboarding Agent",
)

origins = [
    value.strip()
    for value in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if value.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router, prefix="/api")
app.include_router(repositories.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(benchmarks.router, prefix="/api")
