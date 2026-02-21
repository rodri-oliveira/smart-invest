"""API FastAPI do Smart Invest."""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aim.config.settings import get_settings
from aim.data_layer.database import Database
from api.routers import assets, auth, health, portfolio, recommendation, signals, simulation

settings = get_settings()
logger = logging.getLogger("smart_invest.auto_update")
STATE_FILE = Path("data/auto_update_state.json")

_scheduler: Optional[BackgroundScheduler] = None
_current_update_process: Optional[subprocess.Popen] = None

app = FastAPI(
    title="Smart Invest API",
    description="API de inteligencia estrategica para investimentos quantitativos",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS
dev_origin_regex = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$" if settings.is_development else None
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.cors_origins else [],
    allow_origin_regex=settings.cors_allow_origin_regex or dev_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(assets.router, prefix="/assets", tags=["Assets"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(recommendation.router, prefix="/recommendation", tags=["Recomendacao"])
app.include_router(simulation.router, prefix="/simulation", tags=["Simulacao"])


def _read_auto_update_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_auto_update_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _mark_update_trigger(source: str) -> None:
    state = _read_auto_update_state()
    state["last_trigger_date"] = _today_str()
    state["last_trigger_at"] = datetime.now().isoformat(timespec="seconds")
    state["last_trigger_source"] = source
    _write_auto_update_state(state)


def _compute_data_freshness() -> Tuple[bool, Dict[str, Any]]:
    db = Database()
    prices = db.fetch_one("SELECT MAX(date) as max_date FROM prices")
    scores = db.fetch_one("SELECT MAX(date) as max_date FROM signals")
    universe = db.fetch_one("SELECT COUNT(*) as count FROM assets WHERE is_active = 1")

    prices_date = prices["max_date"] if prices else None
    scores_date = scores["max_date"] if scores else None
    active_universe = int(universe["count"]) if universe and universe.get("count") is not None else 0

    prices_count_latest = 0
    scores_count_latest = 0
    if prices_date:
        prices_latest = db.fetch_one(
            "SELECT COUNT(DISTINCT ticker) as count FROM prices WHERE date = ?",
            (prices_date,),
        )
        prices_count_latest = int(prices_latest["count"]) if prices_latest else 0
    if scores_date:
        scores_latest = db.fetch_one(
            "SELECT COUNT(DISTINCT ticker) as count FROM signals WHERE date = ?",
            (scores_date,),
        )
        scores_count_latest = int(scores_latest["count"]) if scores_latest else 0

    prices_coverage = (prices_count_latest / active_universe) if active_universe > 0 else 0.0
    scores_coverage = (scores_count_latest / active_universe) if active_universe > 0 else 0.0

    days_diff = None
    is_fresh = False
    if prices_date and scores_date:
        days_diff_row = db.fetch_one(
            "SELECT julianday('now') - julianday(?) as diff",
            (prices_date,),
        )
        days_diff = float(days_diff_row["diff"]) if days_diff_row else None
        is_recent = (days_diff is not None) and (days_diff <= 3.0)
        has_coverage = prices_coverage >= 0.70 and scores_coverage >= 0.70
        is_fresh = is_recent and has_coverage

    context = {
        "prices_date": prices_date,
        "scores_date": scores_date,
        "active_universe": active_universe,
        "prices_count": prices_count_latest,
        "scores_count": scores_count_latest,
        "prices_coverage": round(prices_coverage, 3),
        "scores_coverage": round(scores_coverage, 3),
        "days_since_prices": round(days_diff, 2) if days_diff is not None else None,
    }
    return is_fresh, context


def _trigger_daily_update(source: str) -> bool:
    global _current_update_process
    script_path = Path(os.getcwd()) / "scripts" / "daily_update.py"
    if not script_path.exists():
        logger.warning("Auto update skip: script not found at %s", script_path)
        return False

    if _current_update_process and _current_update_process.poll() is None:
        logger.info("Auto update skip: another update process is still running")
        return False

    _current_update_process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.getcwd(),
    )
    _mark_update_trigger(source)
    logger.info("Auto update triggered from %s with pid %s", source, _current_update_process.pid)
    return True


def _startup_auto_update_check() -> None:
    if not settings.auto_update_on_startup:
        return
    is_fresh, context = _compute_data_freshness()
    if is_fresh:
        logger.info("Auto update startup skipped: data already fresh (%s)", context)
        return
    _trigger_daily_update(source="startup")


def _scheduled_auto_update_job() -> None:
    is_fresh, context = _compute_data_freshness()
    if is_fresh:
        logger.info("Auto update schedule skipped: data already fresh (%s)", context)
        return
    _trigger_daily_update(source="scheduler")


@app.on_event("startup")
def on_startup() -> None:
    global _scheduler
    _startup_auto_update_check()

    if not settings.auto_update_daily_schedule:
        return

    _scheduler = BackgroundScheduler()
    day_of_week = "mon-fri" if settings.auto_update_weekdays_only else "*"
    trigger = CronTrigger(
        day_of_week=day_of_week,
        hour=settings.auto_update_hour,
        minute=settings.auto_update_minute,
    )
    _scheduler.add_job(
        _scheduled_auto_update_job,
        trigger=trigger,
        id="daily_data_update",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Auto update scheduler started: %s %02d:%02d",
        day_of_week,
        settings.auto_update_hour,
        settings.auto_update_minute,
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "name": "Smart Invest API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
    }
