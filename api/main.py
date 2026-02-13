"""API FastAPI do Smart Invest."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aim.config.settings import get_settings
from api.routers import assets, health, portfolio, signals

settings = get_settings()

app = FastAPI(
    title="Smart Invest API",
    description="API de inteligência estratégica para investimentos quantitativos",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(assets.router, prefix="/assets", tags=["Assets"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "name": "Smart Invest API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
    }
