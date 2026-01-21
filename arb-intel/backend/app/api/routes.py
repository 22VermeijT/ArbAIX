"""API routes for the arbitrage intelligence platform.

All endpoints are read-only and advisory.
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from typing import Literal

from ..core.models import Opportunity, ScanResult
from ..engine import (
    scanner,
    run_single_scan,
    format_opportunity_json,
    format_opportunities_table,
    generate_disclaimer,
)
from ..config import DEFAULT_STAKE_USD


router = APIRouter(prefix="/api", tags=["opportunities"])


@router.get("/")
async def root():
    """API root - health check and info."""
    return {
        "status": "ok",
        "service": "Arbitrage Intelligence Platform",
        "version": "1.0.0",
        "advisory_only": True,
        "disclaimer": generate_disclaimer(),
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scanner_running": scanner.is_running,
        "last_scan": scanner.last_scan.isoformat() if scanner.last_scan else None,
        "markets_cached": len(scanner.markets),
        "opportunities_count": len(scanner.opportunities),
    }


@router.get("/opportunities")
async def get_opportunities(
    type: Literal["ARBITRAGE", "EV", "all"] = "all",
    min_profit: float = Query(0.0, ge=0, description="Minimum profit %"),
    risk: Literal["LOW", "MEDIUM", "HIGH", "all"] = "all",
    sport: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    format: Literal["json", "text"] = "json",
):
    """
    Get current opportunities.

    Filters:
    - type: ARBITRAGE, EV, or all
    - min_profit: Minimum profit percentage
    - risk: LOW, MEDIUM, HIGH, or all
    - sport: Filter by sport/category
    - limit: Max results to return
    - format: json or text output
    """
    opportunities = scanner.opportunities

    # Apply filters
    if type != "all":
        opportunities = [o for o in opportunities if o.type == type]

    if min_profit > 0:
        opportunities = [o for o in opportunities if o.expected_profit_pct >= min_profit]

    if risk != "all":
        opportunities = [o for o in opportunities if o.risk == risk]

    if sport:
        sport_lower = sport.lower()
        opportunities = [
            o for o in opportunities
            if sport_lower in o.event_name.lower()
        ]

    # Limit results
    opportunities = opportunities[:limit]

    if format == "text":
        return {
            "text": format_opportunities_table(opportunities),
            "disclaimer": generate_disclaimer(),
        }

    return {
        "count": len(opportunities),
        "opportunities": [format_opportunity_json(o) for o in opportunities],
        "disclaimer": generate_disclaimer(),
    }


@router.get("/opportunities/{event_id}")
async def get_opportunity_detail(event_id: str):
    """Get detailed opportunity for a specific event."""
    opportunities = [o for o in scanner.opportunities if o.event_id == event_id]

    if not opportunities:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "event_id": event_id,
        "opportunities": [format_opportunity_json(o) for o in opportunities],
        "disclaimer": generate_disclaimer(),
    }


@router.post("/scan")
async def trigger_scan(
    stake: float = Query(DEFAULT_STAKE_USD, ge=10, le=100000),
):
    """
    Trigger a manual scan cycle.

    Returns fresh opportunities.
    """
    result = await run_single_scan()

    return {
        "success": True,
        "markets_scanned": result.markets_scanned,
        "opportunities_found": len(result.opportunities),
        "scan_duration_ms": result.scan_duration_ms,
        "timestamp": result.timestamp.isoformat(),
        "opportunities": [format_opportunity_json(o) for o in result.opportunities[:20]],
        "disclaimer": generate_disclaimer(),
    }


@router.get("/markets")
async def get_markets(
    sport: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get cached markets.

    For debugging and transparency.
    """
    markets = scanner.markets

    if sport:
        sport_lower = sport.lower()
        markets = [m for m in markets if sport_lower in m.sport.lower()]

    markets = markets[:limit]

    return {
        "count": len(markets),
        "markets": [
            {
                "event_id": m.event_id,
                "sport": m.sport,
                "event_name": m.event_name,
                "market_type": m.market_type,
                "outcomes": [
                    {
                        "name": o.name,
                        "odds_decimal": o.odds_decimal,
                        "venue": o.venue,
                    }
                    for o in m.outcomes
                ],
                "start_time": m.start_time.isoformat() if m.start_time else None,
            }
            for m in markets
        ],
    }


@router.get("/stats")
async def get_stats():
    """Get scanner statistics."""
    opportunities = scanner.opportunities

    arb_count = len([o for o in opportunities if o.type == "ARBITRAGE"])
    ev_count = len([o for o in opportunities if o.type == "EV"])

    avg_profit = 0.0
    if opportunities:
        avg_profit = sum(o.expected_profit_pct for o in opportunities) / len(opportunities)

    return {
        "scanner_running": scanner.is_running,
        "last_scan": scanner.last_scan.isoformat() if scanner.last_scan else None,
        "total_markets": len(scanner.markets),
        "total_opportunities": len(opportunities),
        "arbitrage_count": arb_count,
        "ev_count": ev_count,
        "average_profit_pct": round(avg_profit, 4),
        "by_risk": {
            "low": len([o for o in opportunities if o.risk == "LOW"]),
            "medium": len([o for o in opportunities if o.risk == "MEDIUM"]),
            "high": len([o for o in opportunities if o.risk == "HIGH"]),
        },
    }


@router.get("/sources")
async def get_sources():
    """Get data source statistics."""
    markets = scanner.markets

    # Count markets by venue
    venue_counts: dict[str, int] = {}
    for market in markets:
        for outcome in market.outcomes:
            venue = outcome.venue
            if venue not in venue_counts:
                venue_counts[venue] = 0
            venue_counts[venue] += 1
            break  # Only count once per market

    # Define all sources with their info
    known_venues = ["kalshi", "polymarket", "manifold", "predictit"]
    sources = [
        {
            "name": "Kalshi",
            "id": "kalshi",
            "type": "Prediction Market",
            "description": "CFTC-regulated event contracts",
            "markets": venue_counts.get("kalshi", 0),
            "status": "active" if venue_counts.get("kalshi", 0) > 0 else "inactive",
            "url": "https://kalshi.com",
        },
        {
            "name": "PredictIt",
            "id": "predictit",
            "type": "Prediction Market",
            "description": "Political prediction market",
            "markets": venue_counts.get("predictit", 0),
            "status": "active" if venue_counts.get("predictit", 0) > 0 else "inactive",
            "url": "https://www.predictit.org",
        },
        {
            "name": "Polymarket",
            "id": "polymarket",
            "type": "Prediction Market",
            "description": "Crypto-based prediction market",
            "markets": venue_counts.get("polymarket", 0),
            "status": "active" if venue_counts.get("polymarket", 0) > 0 else "inactive",
            "url": "https://polymarket.com",
        },
        {
            "name": "Manifold",
            "id": "manifold",
            "type": "Play Money",
            "description": "Play-money predictions (probability anchor)",
            "markets": venue_counts.get("manifold", 0),
            "status": "active" if venue_counts.get("manifold", 0) > 0 else "inactive",
            "url": "https://manifold.markets",
        },
        {
            "name": "The Odds API",
            "id": "oddsapi",
            "type": "Sportsbooks",
            "description": "Aggregated odds from 10+ bookmakers",
            "markets": sum(v for k, v in venue_counts.items() if k not in known_venues),
            "status": "active" if any(k not in known_venues for k in venue_counts) else "api_key_exhausted",
            "url": "https://the-odds-api.com",
        },
    ]

    return {
        "sources": sources,
        "total_markets": len(markets),
        "active_sources": len([s for s in sources if s["status"] == "active"]),
    }
