"""Core mathematical functions for arbitrage and EV detection.

All functions are pure and have no side effects.

Key Formulas:
- Implied Probability: P = 1 / decimal_odds
- Arbitrage Condition: P1 + P2 < 1 - fees
- Arbitrage Profit %: (1 - (P1 + P2 + fees)) * 100
"""

from typing import NamedTuple


class ArbitrageResult(NamedTuple):
    """Result of arbitrage detection."""
    is_arbitrage: bool
    profit_pct: float
    implied_prob_sum: float
    margin: float  # How much below 1 (or above for no arb)


def calculate_implied_probability(decimal_odds: float) -> float:
    """
    Calculate implied probability from decimal odds.

    Formula: P = 1 / decimal_odds

    Examples:
        2.00 → 0.50 (50%)
        1.50 → 0.667 (66.7%)
        3.00 → 0.333 (33.3%)
    """
    if decimal_odds <= 1.0:
        raise ValueError(f"Decimal odds must be > 1.0, got {decimal_odds}")
    return 1.0 / decimal_odds


def detect_arbitrage(
    decimal_odds: list[float],
    total_fee_pct: float = 0.0
) -> ArbitrageResult:
    """
    Detect if arbitrage exists for a set of outcomes.

    Two-Outcome Arbitrage Condition:
        P1 + P2 < 1 - total_fees

    Where Pn = 1 / decimal_odds_n

    Arbitrage Profit %:
        profit_pct = (1 - (P1 + P2 + fees)) * 100

    Args:
        decimal_odds: List of decimal odds for each outcome
        total_fee_pct: Total fees as percentage (e.g., 2.0 for 2%)

    Returns:
        ArbitrageResult with detection results
    """
    if len(decimal_odds) < 2:
        raise ValueError("Need at least 2 outcomes to check arbitrage")

    # Calculate implied probabilities
    implied_probs = [calculate_implied_probability(odds) for odds in decimal_odds]
    prob_sum = sum(implied_probs)

    # Account for fees
    fee_decimal = total_fee_pct / 100
    threshold = 1.0 - fee_decimal

    # Check arbitrage condition
    is_arb = prob_sum < threshold
    margin = threshold - prob_sum
    profit_pct = margin * 100 if is_arb else 0.0

    return ArbitrageResult(
        is_arbitrage=is_arb,
        profit_pct=profit_pct,
        implied_prob_sum=prob_sum,
        margin=margin
    )


def calculate_ev(
    decimal_odds: float,
    true_probability: float,
    stake: float = 100.0,
    fee_pct: float = 0.0
) -> float:
    """
    Calculate Expected Value for a bet.

    EV = (P_true * payout) - stake - fees

    Args:
        decimal_odds: Offered decimal odds
        true_probability: Estimated true probability of outcome
        stake: Bet amount
        fee_pct: Fee percentage

    Returns:
        Expected value in same units as stake
    """
    payout = stake * decimal_odds
    fee = stake * (fee_pct / 100)
    ev = (true_probability * payout) - stake - fee
    return ev


def calculate_ev_pct(
    decimal_odds: float,
    true_probability: float,
    fee_pct: float = 0.0
) -> float:
    """
    Calculate EV as percentage of stake.

    EV% = ((P_true * decimal_odds) - 1 - fee_pct/100) * 100

    Args:
        decimal_odds: Offered decimal odds
        true_probability: Estimated true probability
        fee_pct: Fee percentage

    Returns:
        EV as percentage (e.g., 5.0 for 5% edge)
    """
    gross_ev_pct = (true_probability * decimal_odds - 1) * 100
    return gross_ev_pct - fee_pct


def calculate_kelly_fraction(
    decimal_odds: float,
    true_probability: float,
    fee_pct: float = 0.0
) -> float:
    """
    Calculate Kelly Criterion fraction for optimal bet sizing.

    Kelly f = (p * (b + 1) - 1) / b

    Where:
        p = true probability
        b = decimal_odds - 1 (net odds)

    Args:
        decimal_odds: Offered decimal odds
        true_probability: Estimated true probability
        fee_pct: Fee percentage (reduces effective odds)

    Returns:
        Kelly fraction (0 to 1, or negative if -EV)
    """
    # Adjust odds for fees
    effective_odds = decimal_odds * (1 - fee_pct / 100)
    b = effective_odds - 1

    if b <= 0:
        return 0.0

    kelly = (true_probability * (b + 1) - 1) / b
    return max(0.0, kelly)  # Don't return negative fractions


def find_best_odds(
    outcomes_by_venue: dict[str, float]  # venue -> decimal_odds
) -> tuple[str, float]:
    """
    Find the best odds across venues for a single outcome.

    Args:
        outcomes_by_venue: Dictionary mapping venue to decimal odds

    Returns:
        Tuple of (best_venue, best_odds)
    """
    if not outcomes_by_venue:
        raise ValueError("No outcomes provided")

    best_venue = max(outcomes_by_venue, key=outcomes_by_venue.get)
    return best_venue, outcomes_by_venue[best_venue]
