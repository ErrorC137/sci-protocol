"""UPLO API (hackathon rebrand of SCI Protocol)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .chain.indexer import start_indexer
from .config import settings
from .deps import get_store
from .routers import chain, core, forms

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_store()  # load corpus + embeddings before the first request, not during it
    ix = start_indexer()
    yield
    if ix:
        ix.stop()


app = FastAPI(
    title="UPLO API",
    version="0.1.0",
    description="Non-confidential research-funding matching, application pre-fill, and testnet milestone escrow.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(core.router)
app.include_router(forms.router)
app.include_router(chain.router)
