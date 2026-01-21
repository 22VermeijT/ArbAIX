"""Manifold Markets data ingestion client.

Manifold is a play-money prediction market.
Useful as a probability anchor for EV calculations.

API Documentation: https://docs.manifold.markets/api
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Any

from ..core.models import Market, Outcome
from ..config import MANIFOLD_API_KEY


MANIFOLD_BASE_URL = "https://api.manifold.markets/v0"


class ManifoldClient:
    """Async client for Manifold Markets API."""

    def __init__(self, api_key: str = MANIFOLD_API_KEY):
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: dict | None = None) -> Any:
        """Make async GET request."""
        session = await self._get_session()
        url = f"{MANIFOLD_BASE_URL}{endpoint}"
        headers = {"Accept": "application/json"}

        if self.api_key and self.api_key != "PLACEHOLDER":
            headers["Authorization"] = f"Key {self.api_key}"

        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    print(f"Manifold API error: {resp.status} - {text[:200]}")
                    return None
        except asyncio.TimeoutError:
            print("Manifold API timeout")
            return None
        except Exception as e:
            print(f"Manifold API error: {e}")
            return None

    async def get_markets(
        self,
        limit: int = 100,
        sort: str = "last-bet-time"
    ) -> list[dict]:
        """
        Fetch markets from Manifold.

        Sort options: created-time, updated-time, last-bet-time, last-comment-time
        """
        params = {
            "limit": limit,
            "sort": sort,
            "order": "desc",
        }
        data = await self._request("/markets", params)
        if data is None:
            return []

        return data if isinstance(data, list) else []

    async def get_market(self, market_id: str) -> dict | None:
        """Fetch single market by ID or slug."""
        return await self._request(f"/market/{market_id}")

    async def search_markets(self, query: str, limit: int = 20) -> list[dict]:
        """Search markets by query."""
        params = {"term": query, "limit": limit}
        data = await self._request("/search-markets", params)
        if data is None:
            return []
        return data if isinstance(data, list) else []

    def _parse_market(self, raw: dict) -> Market | None:
        """
        Parse raw Manifold market into canonical Market model.

        Manifold markets have:
        - id: Market ID
        - question: Market question
        - probability: Current probability (0-1) for binary markets
        - outcomeType: BINARY, MULTIPLE_CHOICE, etc.
        """
        try:
            market_id = raw.get("id", "")
            question = raw.get("question", "")
            outcome_type = raw.get("outcomeType", "")

            # Only handle binary markets for now
            if outcome_type == "BINARY":
                prob = raw.get("probability", 0.5)

                # Clamp probability
                prob = max(0.01, min(0.99, prob))

                yes_odds = 1 / prob
                no_odds = 1 / (1 - prob)

                outcomes = [
                    Outcome(
                        name="Yes",
                        odds_decimal=round(yes_odds, 4),
                        venue="manifold",
                        liquidity=raw.get("totalLiquidity")
                    ),
                    Outcome(
                        name="No",
                        odds_decimal=round(no_odds, 4),
                        venue="manifold",
                        liquidity=raw.get("totalLiquidity")
                    )
                ]

            elif outcome_type == "MULTIPLE_CHOICE":
                answers = raw.get("answers", [])
                if not answers:
                    return None

                outcomes = []
                for ans in answers:
                    prob = ans.get("probability", 0)
                    if prob <= 0 or prob >= 1:
                        continue
                    odds = 1 / prob
                    outcomes.append(Outcome(
                        name=ans.get("text", "Unknown"),
                        odds_decimal=round(odds, 4),
                        venue="manifold",
                        liquidity=None
                    ))

                if len(outcomes) < 2:
                    return None
            else:
                return None

            # Get group/category
            groups = raw.get("groupSlugs", [])
            category = groups[0] if groups else "prediction"

            # Parse close time
            close_time = raw.get("closeTime")
            start_time = None
            if close_time:
                try:
                    start_time = datetime.fromtimestamp(close_time / 1000)
                except:
                    pass

            return Market(
                event_id=f"manifold_{market_id}",
                sport=category,
                event_name=question,
                market_type="binary" if outcome_type == "BINARY" else "multi",
                outcomes=outcomes,
                start_time=start_time
            )

        except Exception as e:
            print(f"Error parsing Manifold market: {e}")
            return None

    async def fetch_markets(self) -> list[Market]:
        """
        Fetch and parse active markets.

        Returns list of canonical Market objects.
        """
        raw_markets = await self.get_markets(limit=100, sort="last-bet-time")

        if raw_markets is None:
            print("Manifold: API returned None")
            return []

        print(f"Manifold: got {len(raw_markets)} raw markets from API")
        markets = []

        for raw in raw_markets:
            # Skip resolved markets
            if raw.get("isResolved", False):
                continue

            market = self._parse_market(raw)
            if market:
                markets.append(market)

        if markets:
            print(f"Manifold: parsed {len(markets)} active markets")
        else:
            print("Manifold: no markets parsed successfully")
        return markets


# Singleton instance
manifold_client = ManifoldClient()


async def fetch_manifold_markets() -> list[Market]:
    """Convenience function to fetch Manifold markets."""
    return await manifold_client.fetch_markets()
