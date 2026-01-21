"""Betfair Exchange data ingestion client (read-only).

Betfair is a betting exchange with deep liquidity.
Used as a probability anchor for +EV calculations.

Note: Requires API key for full access. This implementation
uses placeholder endpoints.

API Documentation: https://docs.developer.betfair.com/
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Any

from ..core.models import Market, Outcome
from ..config import BETFAIR_API_KEY


# Betfair API endpoints
BETFAIR_API_URL = "https://api.betfair.com/exchange/betting/rest/v1.0"
BETFAIR_LOGIN_URL = "https://identitysso.betfair.com/api/login"


class BetfairClient:
    """
    Async client for Betfair Exchange API (read-only).

    Note: Full functionality requires valid API credentials.
    This implementation provides the structure for integration.
    """

    def __init__(self, api_key: str = BETFAIR_API_KEY):
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._session_token: str | None = None

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

    def _get_headers(self) -> dict:
        """Get API headers."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key and self.api_key != "PLACEHOLDER":
            headers["X-Application"] = self.api_key
        if self._session_token:
            headers["X-Authentication"] = self._session_token
        return headers

    async def _request(
        self,
        endpoint: str,
        method: str = "POST",
        data: dict | None = None
    ) -> Any:
        """Make async request to Betfair API."""
        if self.api_key == "PLACEHOLDER":
            # Return mock data for testing
            return self._get_mock_data(endpoint)

        session = await self._get_session()
        url = f"{BETFAIR_API_URL}/{endpoint}/"
        headers = self._get_headers()

        try:
            if method == "POST":
                async with session.post(url, json=data, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    print(f"Betfair API error: {resp.status}")
                    return None
            else:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except asyncio.TimeoutError:
            print("Betfair API timeout")
            return None
        except Exception as e:
            print(f"Betfair API error: {e}")
            return None

    def _get_mock_data(self, endpoint: str) -> list | dict | None:
        """Return mock data when no API key is configured."""
        # Provide sample data structure for development
        if "listEventTypes" in endpoint:
            return [{"eventType": {"id": "7", "name": "Horse Racing"}}]
        if "listMarketCatalogue" in endpoint:
            return []
        return None

    async def get_event_types(self) -> list[dict]:
        """Get list of event types (sports)."""
        data = {"filter": {}}
        result = await self._request("listEventTypes", data=data)
        return result if result else []

    async def get_events(
        self,
        event_type_id: str,
        market_countries: list[str] | None = None
    ) -> list[dict]:
        """Get events for a sport."""
        filter_params = {"eventTypeIds": [event_type_id]}
        if market_countries:
            filter_params["marketCountries"] = market_countries

        data = {"filter": filter_params}
        result = await self._request("listEvents", data=data)
        return result if result else []

    async def get_market_catalogue(
        self,
        event_ids: list[str],
        market_types: list[str] | None = None,
        max_results: int = 100
    ) -> list[dict]:
        """Get market catalogue for events."""
        filter_params = {"eventIds": event_ids}
        if market_types:
            filter_params["marketTypeCodes"] = market_types

        data = {
            "filter": filter_params,
            "maxResults": max_results,
            "marketProjection": ["RUNNER_METADATA", "EVENT"]
        }
        result = await self._request("listMarketCatalogue", data=data)
        return result if result else []

    async def get_market_book(self, market_ids: list[str]) -> list[dict]:
        """Get current prices for markets."""
        data = {
            "marketIds": market_ids,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"],
                "virtualise": False
            }
        }
        result = await self._request("listMarketBook", data=data)
        return result if result else []

    def _parse_market(self, catalogue: dict, book: dict | None = None) -> Market | None:
        """
        Parse Betfair market data into canonical Market model.

        Betfair structure:
        - marketId: Unique market ID
        - marketName: Market name
        - runners: List of selections
        - event: Event info
        """
        try:
            market_id = catalogue.get("marketId", "")
            market_name = catalogue.get("marketName", "")
            event = catalogue.get("event", {})
            event_name = event.get("name", market_name)
            runners = catalogue.get("runners", [])

            if not runners:
                return None

            outcomes = []
            for runner in runners:
                selection_id = runner.get("selectionId")
                runner_name = runner.get("runnerName", f"Selection {selection_id}")

                # Get prices from book if available
                odds = 2.0  # Default
                if book:
                    book_runners = book.get("runners", [])
                    for br in book_runners:
                        if br.get("selectionId") == selection_id:
                            ex = br.get("ex", {})
                            back_prices = ex.get("availableToBack", [])
                            if back_prices:
                                odds = back_prices[0].get("price", 2.0)
                            break

                outcomes.append(Outcome(
                    name=runner_name,
                    odds_decimal=odds,
                    venue="betfair",
                    liquidity=None
                ))

            if len(outcomes) < 2:
                return None

            # Determine sport from event type
            sport = "sports"

            return Market(
                event_id=f"betfair_{market_id}",
                sport=sport,
                event_name=event_name,
                market_type="moneyline",
                outcomes=outcomes,
                start_time=None
            )

        except Exception as e:
            print(f"Error parsing Betfair market: {e}")
            return None

    async def fetch_markets(self, sport_id: str = "7") -> list[Market]:
        """
        Fetch and parse markets for a sport.

        Default sport_id 7 = Horse Racing
        1 = Soccer, 2 = Tennis, etc.

        Note: Requires valid API credentials for real data.
        """
        if self.api_key == "PLACEHOLDER":
            # Return empty list when no API key
            return []

        # Get events
        events = await self.get_events(sport_id)
        if not events:
            return []

        event_ids = [e.get("event", {}).get("id") for e in events[:20]]
        event_ids = [eid for eid in event_ids if eid]

        if not event_ids:
            return []

        # Get market catalogue
        catalogues = await self.get_market_catalogue(event_ids)
        if not catalogues:
            return []

        # Get prices
        market_ids = [c.get("marketId") for c in catalogues[:50]]
        books = await self.get_market_book(market_ids)
        book_map = {b.get("marketId"): b for b in books} if books else {}

        # Parse markets
        markets = []
        for cat in catalogues:
            market_id = cat.get("marketId")
            book = book_map.get(market_id)
            market = self._parse_market(cat, book)
            if market:
                markets.append(market)

        return markets


# Singleton instance
betfair_client = BetfairClient()


async def fetch_betfair_markets(sport_id: str = "7") -> list[Market]:
    """Convenience function to fetch Betfair markets."""
    return await betfair_client.fetch_markets(sport_id)
