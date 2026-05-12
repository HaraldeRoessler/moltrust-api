"""Dev-Server for Explorer Phase A. Port 8099.
Production main.py stays untouched."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.explorer.routes import router as explorer_router

app = FastAPI(
    title="MolTrust Explorer (Dev)",
    description="Phase A — Backend for Know Your Agent Explorer",
    version="0.1.0-dev",
)

# Dev origins only — explicit allowlist instead of "*". If this dev server
# is ever exposed beyond localhost, override via MOLTRUST_DEV_CORS_ORIGINS
# (comma-separated). Wildcard CORS in dev has historically leaked into prod.
_DEFAULT_DEV_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8099"
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("MOLTRUST_DEV_CORS_ORIGINS", _DEFAULT_DEV_ORIGINS).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
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
