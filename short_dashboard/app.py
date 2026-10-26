from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .engine.pipeline import ShortSellerDashboardEngine

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="US Equity Quant Short-Biased Monitor & Decision Dashboard",
    version="1.0.0",
    description="Quantitative multi-factor short scoring, macro regime filter, execution trigger engine, and portfolio correlation risk monitor.",
)

engine = ShortSellerDashboardEngine()
_cached_scan: Optional[Dict[str, Any]] = None


class WatchlistUpdate(BaseModel):
    ticker: str


class InstitutionalOverridePayload(BaseModel):
    ticker: str
    borrow_fee_rate_pct: Optional[float] = None
    short_pct_float: Optional[float] = None
    days_to_cover: Optional[float] = None
    days_to_earnings: Optional[int] = None
    dilution_offering_flag: Optional[bool] = None
    gamma_exposure_regime: Optional[str] = None


class AccountConfigPayload(BaseModel):
    account_size: float = 100_000.0
    base_risk_pct: float = 0.75


@app.get("/api/dashboard")
def get_dashboard(refresh: bool = False) -> JSONResponse:
    global _cached_scan
    if _cached_scan is None or refresh:
        _cached_scan = engine.run_full_scan()
    return JSONResponse(_cached_scan)


@app.get("/api/ticker/{ticker}")
def get_single_ticker(ticker: str) -> JSONResponse:
    try:
        ev = engine.analyze_single_ticker(ticker)
        return JSONResponse(ev.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/ticker/{ticker}/card", response_class=PlainTextResponse)
def get_single_ticker_card(ticker: str) -> PlainTextResponse:
    ev = engine.analyze_single_ticker(ticker)
    return PlainTextResponse(ev.formatted_decision_card)


@app.get("/api/report/daily", response_class=PlainTextResponse)
def get_daily_report_markdown() -> PlainTextResponse:
    global _cached_scan
    if _cached_scan is None:
        _cached_scan = engine.run_full_scan()
    return PlainTextResponse(_cached_scan["daily_report_markdown"])


@app.post("/api/watchlist/add")
def add_to_watchlist(payload: WatchlistUpdate) -> JSONResponse:
    global _cached_scan
    engine.add_ticker(payload.ticker)
    _cached_scan = engine.run_full_scan()
    return JSONResponse(_cached_scan)


@app.post("/api/watchlist/remove")
def remove_from_watchlist(payload: WatchlistUpdate) -> JSONResponse:
    global _cached_scan
    engine.remove_ticker(payload.ticker)
    _cached_scan = engine.run_full_scan()
    return JSONResponse(_cached_scan)


@app.post("/api/override")
def set_institutional_override(payload: InstitutionalOverridePayload) -> JSONResponse:
    global _cached_scan
    overrides: Dict[str, Any] = {}
    if payload.borrow_fee_rate_pct is not None:
        overrides["borrow_fee_rate_pct"] = payload.borrow_fee_rate_pct
    if payload.short_pct_float is not None:
        overrides["short_pct_float"] = payload.short_pct_float / 100.0 if payload.short_pct_float > 1.0 else payload.short_pct_float
    if payload.days_to_cover is not None:
        overrides["days_to_cover"] = payload.days_to_cover
    if payload.days_to_earnings is not None:
        overrides["days_to_earnings"] = payload.days_to_earnings
    if payload.dilution_offering_flag is not None:
        overrides["dilution_offering_flag"] = payload.dilution_offering_flag
    if payload.gamma_exposure_regime is not None:
        overrides["gamma_exposure_regime"] = payload.gamma_exposure_regime

    engine.set_override(payload.ticker, overrides)
    _cached_scan = engine.run_full_scan()
    return JSONResponse(_cached_scan)


@app.post("/api/config")
def update_account_config(payload: AccountConfigPayload) -> JSONResponse:
    global _cached_scan
    engine.account_size = max(1000.0, payload.account_size)
    engine.base_risk_pct = max(0.001, min(0.05, payload.base_risk_pct / 100.0))
    _cached_scan = engine.run_full_scan()
    return JSONResponse(_cached_scan)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/styles.css")
def serve_styles() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "styles.css"))


@app.get("/app.js")
def serve_app_js() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "app.js"))


@app.get("/snapshot.js", response_class=PlainTextResponse)
def serve_empty_snapshot() -> PlainTextResponse:
    return PlainTextResponse("// Live FastAPI mode\n")
