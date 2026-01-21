"""Market scanner orchestrator.

Coordinates data pulls from all sources and triggers
arbitrage/EV detection.

Scan cycle target: ≤2 seconds
"""

import asyncio
from datetime import datetime
from typing import Callable, Awaitable

from ..core.models import Market, Opportunity, ScanResult
from ..core.matcher import find_matching_markets
from ..utils.cache import market_cache
from ..utils.time import Timer
from ..config import SCAN_INTERVAL_SECONDS

from ..ingestion import (
    fetch_polymarket_markets,
    fetch_kalshi_markets,
    fetch_manifold_markets,
    fetch_sportsbook_markets,
    fetch_predictit_markets,
)

from .arbitrage import find_arbitrage_opportunities
from .ev import find_ev_opportunities


class MarketScanner:
    """
    Orchestrates market data collection and opportunity detection.

    Runs continuous scan loops fetching data from all sources
    and detecting arbitrage/EV opportunities.
    """

    def __init__(self):
        self._running = False
        self._markets: dict[str, Market] = {}  # event_id -> Market
        self._opportunities: list[Opportunity] = []
        self._last_scan: datetime | None = None
        self._scan_duration_ms: float = 0
        self._callbacks: list[Callable[[ScanResult], Awaitable[None]]] = []

    @property
    def is_running(self) -> bool:
        """Check if scanner is running."""
        return self._running

    @property
    def markets(self) -> list[Market]:
        """Get all cached markets."""
        return list(self._markets.values())

    @property
    def opportunities(self) -> list[Opportunity]:
        """Get current opportunities."""
        return self._opportunities.copy()

    @property
    def last_scan(self) -> datetime | None:
        """Get timestamp of last scan."""
        return self._last_scan

    def register_callback(
        self,
        callback: Callable[[ScanResult], Awaitable[None]]
    ):
        """Register callback for scan results."""
        self._callbacks.append(callback)

    def unregister_callback(
        self,
        callback: Callable[[ScanResult], Awaitable[None]]
    ):
        """Unregister callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _fetch_all_markets(self) -> list[Market]:
        """
        Fetch markets from all sources concurrently.

        Returns combined list of all markets.
        """
        # Fetch from all sources in parallel
        results = await asyncio.gather(
            fetch_polymarket_markets(),
            fetch_kalshi_markets(),
            fetch_manifold_markets(),
            fetch_sportsbook_markets(),
            fetch_predictit_markets(),
            return_exceptions=True
        )

        all_markets = []
        source_names = ["polymarket", "kalshi", "manifold", "sportsbooks", "predictit"]

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error fetching from {source_names[i]}: {result}")
                continue
            if isinstance(result, list):
                all_markets.extend(result)

        return all_markets

    def _group_markets_by_event(
        self,
        markets: list[Market]
    ) -> dict[str, list[Market]]:
        """
        Group markets by canonical event ID using fuzzy matching.

        Markets from different venues with same event get grouped
        for cross-venue arbitrage detection using similarity matching.
        """
        # Use fuzzy matcher to group same events across platforms
        return find_matching_markets(markets)

    async def scan_once(self) -> ScanResult:
        """
        Perform a single scan cycle.

        1. Fetch markets from all sources
        2. Group by event
        3. Detect arbitrage opportunities
        4. Detect +EV opportunities
        5. Return results
        """
        timer = Timer()
        timer.start()

        # Fetch all markets
        markets = await self._fetch_all_markets()

        # Update cache - use composite key to keep all venue variations
        self._markets.clear()
        for market in markets:
            # Create unique key: event_id + venue
            venue = market.outcomes[0].venue if market.outcomes else "unknown"
            key = f"{market.event_id}_{venue}"
            self._markets[key] = market

        # Group by event for cross-venue analysis
        event_groups = self._group_markets_by_event(markets)

        # Debug: count cross-platform matches
        cross_platform_count = 0
        for event_id, group in event_groups.items():
            venues = set()
            for m in group:
                for o in m.outcomes:
                    venues.add(o.venue)
            if len(venues) > 1:
                cross_platform_count += 1
                if cross_platform_count <= 3:  # Show first 3 examples
                    print(f"  Cross-platform match: {event_id[:50]}...")
                    print(f"    Venues: {venues}")
                    for m in group[:2]:
                        outcomes_str = ", ".join(o.name for o in m.outcomes[:3])
                        print(f"    {m.outcomes[0].venue} [{m.sport}]: {outcomes_str}")

        print(f"Cross-platform groups: {cross_platform_count} / {len(event_groups)} total")

        # Debug: Show sample of unmatched markets per venue
        if cross_platform_count < 5:
            venue_samples: dict[str, list[str]] = {}
            venue_categories: dict[str, set[str]] = {}
            for m in markets:
                venue = m.outcomes[0].venue if m.outcomes else "unknown"
                if venue not in venue_samples:
                    venue_samples[venue] = []
                    venue_categories[venue] = set()
                venue_categories[venue].add(m.sport)
                if len(venue_samples[venue]) < 2:
                    venue_samples[venue].append(f"{m.event_name[:50]}... [{m.sport}]")
            print("Venue categories:")
            for venue, cats in venue_categories.items():
                print(f"  {venue}: {list(cats)[:5]}")

        # Find opportunities
        opportunities = []

        # Arbitrage detection
        arb_opps = find_arbitrage_opportunities(event_groups)
        opportunities.extend(arb_opps)

        # +EV detection (using Manifold as probability anchor)
        ev_opps = find_ev_opportunities(event_groups)
        opportunities.extend(ev_opps)

        # Sort by profit percentage
        opportunities.sort(key=lambda x: x.expected_profit_pct, reverse=True)

        # Update state
        self._opportunities = opportunities
        self._last_scan = datetime.utcnow()

        timer.stop()
        self._scan_duration_ms = timer.elapsed_ms

        result = ScanResult(
            opportunities=opportunities,
            markets_scanned=len(markets),
            scan_duration_ms=self._scan_duration_ms,
            timestamp=self._last_scan
        )

        # Notify callbacks
        for callback in self._callbacks:
            try:
                await callback(result)
            except Exception as e:
                print(f"Callback error: {e}")

        return result

    async def start(self, interval_seconds: float = SCAN_INTERVAL_SECONDS):
        """
        Start continuous scanning loop.

        Args:
            interval_seconds: Time between scans (default from config)
        """
        if self._running:
            return

        self._running = True
        print(f"Scanner started with {interval_seconds}s interval")

        while self._running:
            try:
                result = await self.scan_once()
                print(
                    f"Scan complete: {result.markets_scanned} markets, "
                    f"{len(result.opportunities)} opportunities, "
                    f"{result.scan_duration_ms:.0f}ms"
                )
            except Exception as e:
                print(f"Scan error: {e}")

            # Wait for next cycle
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Stop scanning loop."""
        self._running = False
        print("Scanner stopped")


# Singleton instance
scanner = MarketScanner()


async def run_single_scan() -> ScanResult:
    """Run a single scan and return results."""
    return await scanner.scan_once()


async def start_scanner(interval: float = SCAN_INTERVAL_SECONDS):
    """Start the continuous scanner."""
    await scanner.start(interval)


def stop_scanner():
    """Stop the scanner."""
    scanner.stop()
