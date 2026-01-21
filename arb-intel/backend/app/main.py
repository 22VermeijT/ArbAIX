"""FastAPI application entrypoint.

Cross-Market Arbitrage & Odds Intelligence Platform

ADVISORY-ONLY: This system does not place bets.
All actions must be executed by humans.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router, websocket_endpoint
from .engine import scanner, start_scanner, stop_scanner, generate_disclaimer
from .config import SCAN_INTERVAL_SECONDS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("=" * 60)
    print("Arbitrage Intelligence Platform - Starting")
    print("=" * 60)
    print(generate_disclaimer())
    print("=" * 60)

    # Start scanner in background
    scanner_task = asyncio.create_task(
        start_scanner(SCAN_INTERVAL_SECONDS)
    )

    yield

    # Shutdown
    print("Shutting down scanner...")
    stop_scanner()
    scanner_task.cancel()
    try:
        await scanner_task
    except asyncio.CancelledError:
        pass
    print("Shutdown complete.")


# Create FastAPI app
app = FastAPI(
    title="Arbitrage Intelligence Platform",
    description="""
    Cross-market arbitrage and odds intelligence system.

    **ADVISORY-ONLY**: This system provides information only.
    No bets are placed automatically. All betting decisions
    and executions must be made by humans.

    Features:
    - Real-time odds aggregation from multiple sources
    - Arbitrage opportunity detection
    - +EV (Expected Value) signal detection
    - Stake sizing calculations
    - Human-readable bet instructions

    Sources:
    - Polymarket (prediction market)
    - Kalshi (prediction market)
    - Manifold Markets (probability anchor)
    - Various sportsbook aggregators
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# WebSocket endpoint - must accept connection explicitly
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket_endpoint(websocket)


# Root redirect
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Arbitrage Intelligence Platform",
        "docs": "/docs",
        "api": "/api",
        "websocket": "/ws",
        "disclaimer": generate_disclaimer(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
