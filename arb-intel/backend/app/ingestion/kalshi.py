"""Kalshi data ingestion client.

Kalshi is a regulated prediction market (CFTC-regulated).
Uses RSA key authentication for API access.

API Documentation: https://docs.kalshi.com/
"""

import asyncio
import aiohttp
import base64
import time
from datetime import datetime
from typing import Any
from pathlib import Path

from ..core.models import Market, Outcome

# Kalshi API settings
KALSHI_API_KEY_ID = "a085b1a3-572c-4383-b137-12d7273c34ec"
KALSHI_KEY_PATH = Path(__file__).parent.parent / "kalshi_key.pem"
KALSHI_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


def load_private_key():
    """Load RSA private key for signing."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        if not KALSHI_KEY_PATH.exists():
            print(f"Kalshi key not found at {KALSHI_KEY_PATH}")
            return None

        with open(KALSHI_KEY_PATH, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        return private_key
    except ImportError:
        print("cryptography package not installed - run: pip install cryptography")
        return None
    except Exception as e:
        print(f"Error loading Kalshi key: {e}")
        return None


def sign_request(private_key, timestamp: str, method: str, path: str) -> str:
    """Sign request for Kalshi API authentication using PSS padding."""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        # Message format: timestamp + method + path (without query params)
        message = f"{timestamp}{method}{path}".encode()

        # Kalshi requires PSS padding with MGF1-SHA256, salt_length=digest
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=hashes.SHA256().digest_size
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()
    except Exception as e:
        print(f"Error signing request: {e}")
        return ""


class KalshiClient:
    """Async client for Kalshi API with RSA authentication."""

    def __init__(self):
        self.api_key_id = KALSHI_API_KEY_ID
        self.private_key = load_private_key()
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

    def _get_auth_headers(self, method: str, path: str) -> dict:
        """Generate authentication headers."""
        if not self.private_key:
            return {}

        timestamp = str(int(time.time() * 1000))
        signature = sign_request(self.private_key, timestamp, method, path)

        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

    async def _request(self, endpoint: str, params: dict | None = None, require_auth: bool = False) -> Any:
        """Make async GET request. Auth is optional for read-only endpoints."""
        session = await self._get_session()
        url = f"{KALSHI_BASE_URL}{endpoint}"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Add authentication headers if we have a key and it's required/available
        if self.private_key and require_auth:
            path = f"/trade-api/v2{endpoint}"
            headers.update(self._get_auth_headers("GET", path))

        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    print(f"Kalshi API error {resp.status}: {text[:100]}")
                    return None
        except asyncio.TimeoutError:
            print("Kalshi API timeout")
            return None
        except Exception as e:
            print(f"Kalshi API error: {e}")
            return None

    async def get_markets(
        self,
        limit: int = 100,
        status: str = "open",
    ) -> list[dict]:
        """
        Fetch markets from Kalshi.
        """
        params = {
            "limit": limit,
            "status": status,
        }
        data = await self._request("/markets", params)
        if data is None:
            return []

        return data.get("markets", [])

    def _parse_market(self, raw: dict) -> Market | None:
        """
        Parse raw Kalshi market into canonical Market model.
        """
        try:
            ticker = raw.get("ticker", "")
            title = raw.get("title", "")

            if not ticker or not title:
                return None

            # Get yes/no prices (cents 0-100)
            yes_bid = raw.get("yes_bid", 0) or 0
            yes_ask = raw.get("yes_ask", 100) or 100
            no_bid = raw.get("no_bid", 0) or 0
            no_ask = raw.get("no_ask", 100) or 100

            # Use mid prices
            yes_mid = (yes_bid + yes_ask) / 2 / 100
            no_mid = (no_bid + no_ask) / 2 / 100

            # Clamp to valid range
            yes_mid = max(0.02, min(0.98, yes_mid))
            no_mid = max(0.02, min(0.98, no_mid))

            # Convert to decimal odds
            yes_odds = 1 / yes_mid
            no_odds = 1 / no_mid

            outcomes = [
                Outcome(
                    name="Yes",
                    odds_decimal=round(yes_odds, 4),
                    venue="kalshi",
                    liquidity=raw.get("volume", 0)
                ),
                Outcome(
                    name="No",
                    odds_decimal=round(no_odds, 4),
                    venue="kalshi",
                    liquidity=raw.get("volume", 0)
                )
            ]

            # Get category
            category = raw.get("category", "prediction")
            if not category:
                category = "prediction"

            # Parse close time
            close_time = raw.get("close_time")
            start_time = None
            if close_time:
                try:
                    start_time = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
                except:
                    pass

            return Market(
                event_id=f"kalshi_{ticker}",
                sport=category,
                event_name=title[:200],
                market_type="binary",
                outcomes=outcomes,
                start_time=start_time
            )

        except Exception as e:
            print(f"Error parsing Kalshi market: {e}")
            return None

    async def fetch_markets(self) -> list[Market]:
        """
        Fetch and parse all active markets.
        """
        raw_markets = await self.get_markets(limit=200, status="open")
        markets = []

        for raw in raw_markets:
            market = self._parse_market(raw)
            if market:
                markets.append(market)

        if markets:
            print(f"Kalshi: fetched {len(markets)} active markets")
        return markets


# Singleton instance
kalshi_client = KalshiClient()


async def fetch_kalshi_markets() -> list[Market]:
    """Convenience function to fetch Kalshi markets."""
    return await kalshi_client.fetch_markets()
