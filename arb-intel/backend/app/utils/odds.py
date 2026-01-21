"""Odds conversion utilities.

Supports American, Decimal, and Probability formats.
"""


def american_to_decimal(american_odds: int | float) -> float:
    """
    Convert American odds to Decimal odds.

    American → Decimal:
    - Positive odds: decimal = 1 + odds / 100
    - Negative odds: decimal = 1 + 100 / abs(odds)

    Examples:
        +110 → 2.10
        -110 → 1.909
        +200 → 3.00
        -200 → 1.50
    """
    if american_odds > 0:
        return 1 + american_odds / 100
    else:
        return 1 + 100 / abs(american_odds)


def decimal_to_american(decimal_odds: float) -> int:
    """
    Convert Decimal odds to American odds.

    Decimal → American:
    - If decimal >= 2.0: american = (decimal - 1) * 100
    - If decimal < 2.0: american = -100 / (decimal - 1)

    Examples:
        2.10 → +110
        1.909 → -110
        3.00 → +200
        1.50 → -200
    """
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1) * 100))
    else:
        return int(round(-100 / (decimal_odds - 1)))


def decimal_to_probability(decimal_odds: float) -> float:
    """
    Convert Decimal odds to implied probability.

    probability = 1 / decimal_odds

    Examples:
        2.00 → 0.50 (50%)
        1.50 → 0.667 (66.7%)
        3.00 → 0.333 (33.3%)
    """
    return 1 / decimal_odds


def probability_to_decimal(probability: float) -> float:
    """
    Convert probability to Decimal odds.

    decimal = 1 / probability

    Examples:
        0.50 → 2.00
        0.667 → 1.50
        0.333 → 3.00
    """
    if probability <= 0 or probability >= 1:
        raise ValueError("Probability must be between 0 and 1 (exclusive)")
    return 1 / probability


def american_to_probability(american_odds: int | float) -> float:
    """Convert American odds to implied probability."""
    decimal = american_to_decimal(american_odds)
    return decimal_to_probability(decimal)


def probability_to_american(probability: float) -> int:
    """Convert probability to American odds."""
    decimal = probability_to_decimal(probability)
    return decimal_to_american(decimal)


def format_american_odds(american_odds: int) -> str:
    """Format American odds with + or - prefix."""
    if american_odds > 0:
        return f"+{american_odds}"
    return str(american_odds)


def calculate_overround(probabilities: list[float]) -> float:
    """
    Calculate the overround (vig/juice) from implied probabilities.

    overround = sum(probabilities) - 1

    A fair market has overround = 0.
    Typical sportsbook overround is 0.02-0.10 (2-10%).
    """
    return sum(probabilities) - 1
