"""Stake sizing calculations for arbitrage opportunities.

Key Formulas:
    stake1 = (C * P2) / (P1 + P2)
    stake2 = (C * P1) / (P1 + P2)

    Guaranteed Cashout = stake1 * decimal1 = stake2 * decimal2
    Guaranteed Profit = cashout - C - fees
"""

from typing import NamedTuple
from .math import calculate_implied_probability


class StakeSizing(NamedTuple):
    """Result of stake sizing calculation."""
    stakes: list[float]          # Stake for each outcome
    total_stake: float           # Total capital required
    guaranteed_cashout: float    # Payout regardless of outcome
    guaranteed_profit: float     # Profit after fees
    profit_pct: float           # Profit as percentage


def calculate_stakes(
    decimal_odds: list[float],
    total_capital: float,
    fee_pct: float = 0.0
) -> StakeSizing:
    """
    Calculate optimal stake sizing for arbitrage.

    For a two-outcome market:
        stake1 = (C * P2) / (P1 + P2)
        stake2 = (C * P1) / (P1 + P2)

    Where:
        C = total capital
        Pn = 1 / decimal_odds_n (implied probability)

    This ensures equal cashout regardless of outcome.

    Args:
        decimal_odds: List of decimal odds for each outcome
        total_capital: Total amount to stake across all outcomes
        fee_pct: Total fee percentage to account for

    Returns:
        StakeSizing with stakes and profit calculations
    """
    if len(decimal_odds) < 2:
        raise ValueError("Need at least 2 outcomes for stake sizing")

    # Calculate implied probabilities
    implied_probs = [calculate_implied_probability(odds) for odds in decimal_odds]
    prob_sum = sum(implied_probs)

    # Calculate stakes proportional to other outcomes' probabilities
    # For 2 outcomes: stake1 = C * P2 / (P1 + P2)
    # For N outcomes: stake_i = C * (sum_j!=i P_j) / ((N-1) * sum_all P)
    # Simplified for any N: stake_i = C * (1/odds_i) / sum(1/odds)

    stakes = []
    for i, odds in enumerate(decimal_odds):
        prob = implied_probs[i]
        stake = total_capital * prob / prob_sum
        stakes.append(round(stake, 2))

    # Adjust for rounding to ensure we don't exceed capital
    total_stake = sum(stakes)
    if total_stake > total_capital:
        # Scale down proportionally
        scale = total_capital / total_stake
        stakes = [round(s * scale, 2) for s in stakes]
        total_stake = sum(stakes)

    # Calculate guaranteed cashout (should be same for all outcomes)
    cashouts = [stakes[i] * decimal_odds[i] for i in range(len(stakes))]
    guaranteed_cashout = min(cashouts)  # Use minimum to be conservative

    # Calculate fees
    fees = total_stake * (fee_pct / 100)

    # Calculate profit
    guaranteed_profit = guaranteed_cashout - total_stake - fees
    profit_pct = (guaranteed_profit / total_stake) * 100 if total_stake > 0 else 0

    return StakeSizing(
        stakes=stakes,
        total_stake=total_stake,
        guaranteed_cashout=round(guaranteed_cashout, 2),
        guaranteed_profit=round(guaranteed_profit, 2),
        profit_pct=round(profit_pct, 4)
    )


def calculate_profit(
    stakes: list[float],
    decimal_odds: list[float],
    winning_outcome: int,
    fee_pct: float = 0.0
) -> float:
    """
    Calculate actual profit for a specific outcome winning.

    Args:
        stakes: Amount staked on each outcome
        decimal_odds: Decimal odds for each outcome
        winning_outcome: Index of winning outcome (0-based)
        fee_pct: Fee percentage

    Returns:
        Profit in same units as stakes
    """
    total_stake = sum(stakes)
    fees = total_stake * (fee_pct / 100)
    payout = stakes[winning_outcome] * decimal_odds[winning_outcome]
    return payout - total_stake - fees


def calculate_worst_case_loss(
    stakes: list[float],
    decimal_odds: list[float],
    hedge_probability: float = 1.0
) -> float:
    """
    Calculate worst-case loss if one leg fails to fill.

    worst_case_loss = stake * (1 - hedge_probability)

    This models the scenario where you place one bet but fail
    to hedge the other side.

    Args:
        stakes: Amount staked on each outcome
        decimal_odds: Decimal odds for each outcome
        hedge_probability: Probability of successfully hedging

    Returns:
        Worst case loss (positive number)
    """
    # Worst case: you bet the larger stake and can't hedge
    max_stake = max(stakes)
    return max_stake * (1 - hedge_probability)


def scale_stakes(
    base_stakes: list[float],
    target_profit: float,
    base_profit: float
) -> list[float]:
    """
    Scale stakes to achieve a target profit.

    Args:
        base_stakes: Original stake amounts
        target_profit: Desired profit
        base_profit: Profit from base stakes

    Returns:
        Scaled stake amounts
    """
    if base_profit <= 0:
        raise ValueError("Cannot scale from zero or negative profit")

    scale_factor = target_profit / base_profit
    return [round(s * scale_factor, 2) for s in base_stakes]
