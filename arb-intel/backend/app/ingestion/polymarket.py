"""Polymarket data ingestion client.

Polymarket is a prediction market platform using public APIs.
All access is read-only.

API Documentation: https://docs.polymarket.com/
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Any

from ..core.models import Market, Outcome
from ..core.normalization import generate_event_id
from ..config import POLYMARKET_API_KEY


# Polymarket API endpoints
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"


class PolymarketClient:
    """Async client for Polymarket public API."""

    def __init__(self, api_key: str = POLYMARKET_API_KEY):
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

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

    async def _request(self, url: str, params: dict | None = None) -> Any:
        """Make async GET request."""
        session = await self._get_session()
        headers = {"Accept": "application/json"}

        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"Polymarket API error: {resp.status}")
                    return None
        except asyncio.TimeoutError:
            print("Polymarket API timeout")
            return None
        except Exception as e:
            print(f"Polymarket API error: {e}")
            return None

    async def get_markets(self, limit: int = 100) -> list[dict]:
        """
        Fetch active, open markets from Polymarket.

        Filters for:
        - active=true
        - closed=false
        - Has liquidity
        """
        url = f"{POLYMARKET_GAMMA_URL}/markets"
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": "liquidityNum",
            "ascending": "false",
        }

        data = await self._request(url, params)
        if data is None:
            return []

        return data if isinstance(data, list) else []

    def _parse_market(self, raw: dict) -> Market | None:
        """
        Parse raw Polymarket data into canonical Market model.

        Polymarket markets have:
        - question: The market question
        - outcomes: JSON string like '["Yes", "No"]'
        - outcomePrices: JSON string like '["0.65", "0.35"]'
        - closed: boolean
        - liquidityNum: float
        """
        try:
            # Skip closed markets
            if raw.get("closed", False):
                return None

            # Skip markets with no liquidity
            liquidity = raw.get("liquidityNum", 0)
            if liquidity < 100:  # Minimum $100 liquidity
                return None

            question = raw.get("question", "")
            if not question:
                return None

            # Parse outcomes - may be JSON string or list
            outcomes_raw = raw.get("outcomes", "[]")
            if isinstance(outcomes_raw, str):
                try:
                    outcomes_names = json.loads(outcomes_raw)
                except json.JSONDecodeError:
                    return None
            else:
                outcomes_names = outcomes_raw

            # Parse prices - may be JSON string or list
            prices_raw = raw.get("outcomePrices", "[]")
            if isinstance(prices_raw, str):
                try:
                    prices_str = json.loads(prices_raw)
                except json.JSONDecodeError:
                    return None
            else:
                prices_str = prices_raw

            # Convert prices to floats
            prices = []
            for p in prices_str:
                try:
                    price = float(p)
                    prices.append(price)
                except (ValueError, TypeError):
                    return None

            if len(prices) != len(outcomes_names) or len(prices) < 2:
                return None

            # Convert prices to decimal odds
            # Price is probability (0-1), so odds = 1 / price
            outcomes = []
            for name, price in zip(outcomes_names, prices):
                # Skip invalid prices
                if price <= 0.01 or price >= 0.99:
                    continue

                decimal_odds = 1 / price
                outcomes.append(Outcome(
                    name=name,
                    odds_decimal=round(decimal_odds, 4),
                    venue="polymarket",
                    liquidity=liquidity
                ))

            if len(outcomes) < 2:
                return None

            # Generate event ID
            condition_id = raw.get("conditionId", "")
            market_id = raw.get("id", "")
            event_id = condition_id[:16] if condition_id else market_id

            # Get category
            category = raw.get("category", "prediction")
            if not category:
                category = "prediction"

            return Market(
                event_id=f"polymarket_{event_id}",
                sport=category,
                event_name=question[:200],  # Truncate long questions
                market_type="binary" if len(outcomes) == 2 else "multi",
                outcomes=outcomes,
                start_time=None
            )

        except Exception as e:
            print(f"Error parsing Polymarket market: {e}")
            return None

    async def fetch_markets(self) -> list[Market]:
        """
        Fetch and parse all active markets.

        Returns list of canonical Market objects.
        """
        raw_markets = await self.get_markets(limit=100)
        markets = []

        for raw in raw_markets:
            market = self._parse_market(raw)
            if market:
                markets.append(market)

        print(f"Polymarket: fetched {len(markets)} active markets")
        return markets


# Singleton instance
polymarket_client = PolymarketClient()


async def fetch_polymarket_markets() -> list[Market]:
    """Convenience function to fetch Polymarket markets."""
    return await polymarket_client.fetch_markets()
