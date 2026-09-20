from __future__ import annotations

import logging
import os
from pathlib import Path
from time import monotonic

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .carbon import METHODOLOGY
from .demo import demo_scan
from .models import ScanRequest, ScanResult
from .scanner import live_scan

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"
LIVE_COOLDOWN_SEC = 20.0
_last_live_scan = 0.0

app = FastAPI(title="Ember", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _server_aws_ready() -> bool:
    return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))


@app.get("/api/health")
def health():
    return {"ok": True, "name": "ember"}


@app.get("/api/status")
def status():
    return {
        "ok": True,
        "name": "ember",
        "live_aws": _server_aws_ready(),
        "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    }


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


@app.post("/api/scan/live", response_model=ScanResult)
def scan_live_account(req: ScanRequest):
    """Scan the throwaway demo AWS account configured on the server. Ignores client keys."""
    global _last_live_scan
    if not _server_aws_ready():
        raise HTTPException(
            status_code=503,
            detail="Live AWS demo account is not configured. Use the sample ledger, or run Ember locally with your own keys.",
        )
    now = monotonic()
    if now - _last_live_scan < LIVE_COOLDOWN_SEC:
        raise HTTPException(status_code=429, detail="Live scan is cooling down. Try again in a few seconds.")
    _last_live_scan = now
    server_req = ScanRequest(
        region=os.getenv("AWS_DEFAULT_REGION", req.region),
        lookback_days=req.lookback_days,
        cpu_idle_threshold=req.cpu_idle_threshold,
    )
    try:
        return live_scan(server_req)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
def index():
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        return {"ok": True, "name": "ember", "ui": "not-built"}
    return FileResponse(index_file)


@app.get("/{full_path:path}")
def spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not found")
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="UI not built")
    candidate = FRONTEND_DIST / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(index_file)
