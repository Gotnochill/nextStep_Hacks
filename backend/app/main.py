from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .carbon import METHODOLOGY
from .demo import demo_scan
from .models import ScanRequest, ScanResult
from .scanner import live_scan

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

app = FastAPI(title="Ember", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "name": "ember"}


@app.get("/api/methodology")
def methodology():
    return {"methodology": METHODOLOGY}


@app.get("/api/demo", response_model=ScanResult)
def demo(region: str = "us-east-1", lookback_days: int = 7):
    return demo_scan(region=region, lookback_days=lookback_days)


@app.post("/api/scan", response_model=ScanResult)
def scan(req: ScanRequest):
    try:
        return live_scan(req)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface AWS errors to the UI
        raise HTTPException(status_code=400, detail=str(exc)) from exc
