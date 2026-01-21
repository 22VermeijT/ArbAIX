"""Fee and slippage models for different venues.

Each venue has its own fee structure that must be accounted
for when calculating arbitrage opportunities.
"""

from .models import VenueFees


# Default fee structures by venue (update with real values)
VENUE_FEES: dict[str, VenueFees] = {
    # Prediction Markets
    "polymarket": VenueFees(
        venue="polymarket",
        trading_fee_pct=0.0,  # No trading fees currently
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    "kalshi": VenueFees(
        venue="kalshi",
        trading_fee_pct=0.0,  # Fee embedded in spread
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    "manifold": VenueFees(
        venue="manifold",
        trading_fee_pct=0.0,  # Play money
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    # Betting Exchanges
    "betfair": VenueFees(
        venue="betfair",
        trading_fee_pct=2.0,  # 2% commission on net winnings
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    # Sportsbooks (typical estimates)
    "draftkings": VenueFees(
        venue="draftkings",
        trading_fee_pct=0.0,  # Vig built into odds
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    "fanduel": VenueFees(
        venue="fanduel",
        trading_fee_pct=0.0,  # Vig built into odds
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    "betmgm": VenueFees(
        venue="betmgm",
        trading_fee_pct=0.0,
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
    # Default for unknown venues
    "default": VenueFees(
        venue="default",
        trading_fee_pct=1.0,  # Assume 1% fee for safety
        settlement_fee=0.0,
        withdrawal_fee=0.0,
    ),
}


def get_venue_fees(venue: str) -> VenueFees:
    """
    Get fee structure for a venue.

    Returns default fees if venue not found.
    """
    venue_lower = venue.lower().strip()
    return VENUE_FEES.get(venue_lower, VENUE_FEES["default"])


def calculate_trading_fee(stake: float, venue: str) -> float:
    """
    Calculate trading fee for a bet.

    Returns fee in USD.
    """
    fees = get_venue_fees(venue)
    return stake * (fees.trading_fee_pct / 100)


def calculate_total_fees(
    stakes: list[tuple[float, str]],  # (stake, venue) pairs
) -> float:
    """
    Calculate total fees across multiple bets.

    Args:
        stakes: List of (stake_usd, venue) tuples

    Returns:
        Total fees in USD
    """
    total = 0.0
    for stake, venue in stakes:
        total += calculate_trading_fee(stake, venue)
    return total


def calculate_settlement_fees(venues: list[str]) -> float:
    """
    Calculate total settlement fees across venues.

    Called when opportunity settles.
    """
    total = 0.0
    for venue in venues:
        fees = get_venue_fees(venue)
        total += fees.settlement_fee
    return total


def effective_odds_after_fees(
    decimal_odds: float,
    venue: str,
    is_winner: bool = True
) -> float:
    """
    Calculate effective odds after accounting for venue fees.

    For exchanges like Betfair that charge commission on winnings,
    the effective odds are reduced.

    Args:
        decimal_odds: Original decimal odds
        venue: Venue name
        is_winner: Whether this is the winning outcome (for commission calc)

    Returns:
        Effective decimal odds after fees
    """
    fees = get_venue_fees(venue)

    # If no trading fee, return original odds
    if fees.trading_fee_pct == 0:
        return decimal_odds

    # For exchanges with commission on winnings
    # Effective odds = 1 + (decimal - 1) * (1 - commission)
    if is_winner:
        net_profit_multiplier = 1 - (fees.trading_fee_pct / 100)
        return 1 + (decimal_odds - 1) * net_profit_multiplier

    return decimal_odds
