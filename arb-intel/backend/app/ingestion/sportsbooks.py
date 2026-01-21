"""Sportsbook odds aggregator (read-only, public data only).

Scrapes publicly available odds from aggregator sites.
No login required. Cached and rate-limited.

Sources:
- The Odds API (free tier)
- Public aggregator pages

IMPORTANT: This is advisory-only. No betting, no accounts.
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Any

from ..core.models import Market, Outcome
from ..core.normalization import normalize_team_name, generate_event_id
from ..utils.cache import market_cache
from ..utils.odds import american_to_decimal


# The Odds API - Free tier allows limited requests
# Sign up at: https://the-odds-api.com/
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_KEY = "071ed9fdc01741a94c0d3f6ccd83ba14"  # Free tier key


class SportsOddsClient:
    """
    Client for fetching sportsbook odds from free aggregators.

    Uses The Odds API free tier as primary source.
    """

    def __init__(self, api_key: str = ODDS_API_KEY):
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._request_count = 0
        self._last_request_time: datetime | None = None

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

    async def _request(self, endpoint: str, params: dict | None = None) -> Any:
        """Make async GET request with caching."""
        cache_key = f"odds_api_{endpoint}_{str(params)}"

        # Check cache first
        cached = market_cache.get(cache_key, max_age_seconds=30)
        if cached is not None:
            return cached

        if self.api_key == "PLACEHOLDER":
            # Return mock data for development
            return self._get_mock_data(endpoint)

        session = await self._get_session()
        url = f"{ODDS_API_BASE}{endpoint}"

        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    market_cache.set(cache_key, data)
                    return data
                elif resp.status == 401:
                    print("Odds API: Invalid API key")
                    return None
                elif resp.status == 429:
                    print("Odds API: Rate limited")
                    return None
                else:
                    print(f"Odds API error: {resp.status}")
                    return None
        except asyncio.TimeoutError:
            print("Odds API timeout")
            return None
        except Exception as e:
            print(f"Odds API error: {e}")
            return None

    def _get_mock_data(self, endpoint: str) -> list | dict | None:
        """Return mock data for development without API key."""
        if "/sports" in endpoint and "odds" not in endpoint:
            return [
                {"key": "basketball_nba", "group": "Basketball", "title": "NBA"},
                {"key": "americanfootball_nfl", "group": "American Football", "title": "NFL"},
                {"key": "baseball_mlb", "group": "Baseball", "title": "MLB"},
            ]

        if "/odds" in endpoint:
            # Sample NBA game odds
            return [
                {
                    "id": "sample_game_1",
                    "sport_key": "basketball_nba",
                    "sport_title": "NBA",
                    "commence_time": datetime.utcnow().isoformat() + "Z",
                    "home_team": "Los Angeles Lakers",
                    "away_team": "Boston Celtics",
                    "bookmakers": [
                        {
                            "key": "draftkings",
                            "title": "DraftKings",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Los Angeles Lakers", "price": 2.10},
                                        {"name": "Boston Celtics", "price": 1.85}
                                    ]
                                }
                            ]
                        },
                        {
                            "key": "fanduel",
                            "title": "FanDuel",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Los Angeles Lakers", "price": 2.15},
                                        {"name": "Boston Celtics", "price": 1.80}
                                    ]
                                }
                            ]
                        },
                        {
                            "key": "betmgm",
                            "title": "BetMGM",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Los Angeles Lakers", "price": 2.05},
                                        {"name": "Boston Celtics", "price": 1.90}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]

        return None

    async def get_sports(self) -> list[dict]:
        """Get list of available sports."""
        return await self._request("/sports") or []

    async def get_odds(
        self,
        sport: str,
        regions: str = "us",
        markets: str = "h2h",
        odds_format: str = "decimal"
    ) -> list[dict]:
        """
        Get odds for a sport.

        Args:
            sport: Sport key (e.g., "basketball_nba")
            regions: Region codes (e.g., "us", "uk", "eu")
            markets: Market types (e.g., "h2h", "spreads", "totals")
            odds_format: "decimal" or "american"
        """
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        }
        return await self._request(f"/sports/{sport}/odds", params) or []

    def _parse_event(self, raw: dict) -> list[Market]:
        """
        Parse raw odds data into canonical Market models.

        Creates one Market per venue for cross-venue arbitrage detection.
        """
        markets = []

        try:
            event_id = raw.get("id", "")
            sport = raw.get("sport_key", "")
            sport_title = raw.get("sport_title", sport)
            home_team = raw.get("home_team", "")
            away_team = raw.get("away_team", "")

            commence_time = raw.get("commence_time")
            start_time = None
            if commence_time:
                try:
                    start_time = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                except:
                    pass

            event_name = f"{away_team} @ {home_team}"

            bookmakers = raw.get("bookmakers", [])

            for book in bookmakers:
                venue = book.get("key", "unknown")
                venue_title = book.get("title", venue)

                for mkt in book.get("markets", []):
                    market_type = mkt.get("key", "h2h")

                    outcomes = []
                    for outcome in mkt.get("outcomes", []):
                        name = outcome.get("name", "")
                        price = outcome.get("price", 0)

                        if price <= 1.0:
                            continue

                        outcomes.append(Outcome(
                            name=normalize_team_name(name),
                            odds_decimal=round(price, 4),
                            venue=venue,
                            liquidity=None
                        ))

                    if len(outcomes) >= 2:
                        canonical_id = generate_event_id(
                            sport_title,
                            home_team,
                            away_team,
                            start_time
                        )

                        markets.append(Market(
                            event_id=canonical_id,
                            sport=sport_title,
                            event_name=event_name,
                            market_type="moneyline" if market_type == "h2h" else market_type,
                            outcomes=outcomes,
                            start_time=start_time
                        ))

        except Exception as e:
            print(f"Error parsing sportsbook event: {e}")

        return markets

    async def fetch_markets(
        self,
        sports: list[str] | None = None
    ) -> list[Market]:
        """
        Fetch markets from all configured sportsbooks.

        Args:
            sports: List of sport keys to fetch. Defaults to major US sports.
        """
        if sports is None:
            sports = [
                "basketball_nba",
                "americanfootball_nfl",
                "baseball_mlb",
                "icehockey_nhl",
            ]

        all_markets = []

        for sport in sports:
            raw_events = await self.get_odds(sport)

            for event in raw_events:
                markets = self._parse_event(event)
                all_markets.extend(markets)

        return all_markets


# Singleton instance
sportsbooks_client = SportsOddsClient()


async def fetch_sportsbook_markets(
    sports: list[str] | None = None
) -> list[Market]:
    """Convenience function to fetch sportsbook markets."""
    return await sportsbooks_client.fetch_markets(sports)
