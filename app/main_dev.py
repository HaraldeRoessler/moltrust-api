"""Dev-Server for Explorer Phase A. Port 8099.
Production main.py stays untouched."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.explorer.routes import router as explorer_router

app = FastAPI(
    title="MolTrust Explorer (Dev)",
    description="Phase A — Backend for Know Your Agent Explorer",
    version="0.1.0-dev",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(explorer_router)


@app.get("/")
def root():
    return {
        "service": "MolTrust Explorer Dev",
        "phase": "A",
        "endpoints": [
            "/explorer/stats",
            "/explorer/agents",
            "/explorer/agent/{identifier}",
            "/explorer/methodology",
        ],
    }
