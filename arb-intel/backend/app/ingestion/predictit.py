"""PredictIt data ingestion client.

PredictIt is a political prediction market.
Has overlapping markets with Kalshi for political events.

API is public - no authentication required.
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Any

from ..core.models import Market, Outcome


PREDICTIT_API_URL = "https://www.predictit.org/api/marketdata/all/"


class PredictItClient:
    """Async client for PredictIt API."""

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._cache: list[dict] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 30  # Cache for 30 seconds to avoid rate limits

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_all_markets(self) -> list[dict]:
        """
        Fetch all markets from PredictIt.

        Returns raw market data. Uses caching to avoid rate limits.
        """
        import time

        # Check cache
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        session = await self._get_session()

        try:
            async with session.get(PREDICTIT_API_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = data.get("markets", [])
                    # Update cache
                    self._cache = markets
                    self._cache_time = now
                    return markets
                elif resp.status == 429:
                    # Rate limited - return cached data if available
                    print("PredictIt: rate limited, using cache")
                    return self._cache
                else:
                    text = await resp.text()
                    print(f"PredictIt API error {resp.status}: {text[:100]}")
                    return self._cache  # Return cache on error
        except asyncio.TimeoutError:
            print("PredictIt API timeout")
            return self._cache
        except Exception as e:
            print(f"PredictIt API error: {e}")
            return self._cache

    def _parse_market(self, raw: dict) -> list[Market]:
        """
        Parse raw PredictIt market into canonical Market models.

        PredictIt markets have multiple contracts (outcomes).
        Each contract has Yes/No prices.
        """
        markets = []

        try:
            market_id = raw.get("id", "")
            market_name = raw.get("name", "")
            market_url = raw.get("url", "")

            if not market_id or not market_name:
                return []

            contracts = raw.get("contracts", [])
            if not contracts:
                return []

            # For binary markets (single contract), create Yes/No market
            if len(contracts) == 1:
                contract = contracts[0]
                yes_price = contract.get("lastTradePrice") or contract.get("bestBuyYesCost") or 0.5
                no_price = 1 - yes_price if yes_price else 0.5

                # Skip if no valid price
                if not yes_price or yes_price <= 0.01 or yes_price >= 0.99:
                    return []

                # Convert price (0-1) to decimal odds
                yes_odds = 1 / yes_price if yes_price > 0 else 100
                no_odds = 1 / no_price if no_price > 0 else 100

                # Clamp odds
                yes_odds = min(100, max(1.01, yes_odds))
                no_odds = min(100, max(1.01, no_odds))

                outcomes = [
                    Outcome(
                        name="Yes",
                        odds_decimal=round(yes_odds, 4),
                        venue="predictit",
                        liquidity=None
                    ),
                    Outcome(
                        name="No",
                        odds_decimal=round(no_odds, 4),
                        venue="predictit",
                        liquidity=None
                    )
                ]

                markets.append(Market(
                    event_id=f"predictit_{market_id}",
                    sport="politics",
                    event_name=market_name[:200],
                    market_type="binary",
                    outcomes=outcomes,
                    start_time=None
                ))

            else:
                # Multi-contract market - each contract is an outcome
                outcomes = []
                for contract in contracts:
                    contract_name = contract.get("name", "Unknown")
                    price = contract.get("lastTradePrice") or contract.get("bestBuyYesCost") or 0

                    if not price or price <= 0.01 or price >= 0.99:
                        continue

                    odds = 1 / price
                    odds = min(100, max(1.01, odds))

                    outcomes.append(Outcome(
                        name=contract_name[:50],
                        odds_decimal=round(odds, 4),
                        venue="predictit",
                        liquidity=None
                    ))

                if len(outcomes) >= 2:
                    markets.append(Market(
                        event_id=f"predictit_{market_id}",
                        sport="politics",
                        event_name=market_name[:200],
                        market_type="multi",
                        outcomes=outcomes,
                        start_time=None
                    ))

        except Exception as e:
            print(f"Error parsing PredictIt market: {e}")

        return markets

    async def fetch_markets(self) -> list[Market]:
        """
        Fetch and parse all active markets.

        Returns list of canonical Market objects.
        """
        raw_markets = await self.get_all_markets()

        if not raw_markets:
            return []

        markets = []
        for raw in raw_markets:
            # Skip inactive markets
            status = raw.get("status", "")
            if status and status.lower() != "open":
                continue

            parsed = self._parse_market(raw)
            markets.extend(parsed)

        if markets:
            print(f"PredictIt: {len(markets)} markets (cached 30s)")

        return markets


# Singleton instance
predictit_client = PredictItClient()


async def fetch_predictit_markets() -> list[Market]:
    """Convenience function to fetch PredictIt markets."""
    return await predictit_client.fetch_markets()
