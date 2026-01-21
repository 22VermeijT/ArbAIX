"""Arbitrage opportunity detection.

Finds guaranteed profit opportunities by comparing odds
across different venues.

Arbitrage Condition: P1 + P2 < 1 - fees
Where Pn = 1 / decimal_odds_n
"""

from itertools import combinations
from typing import Literal

from ..core.models import Market, Outcome, Opportunity, BetInstruction
from ..core.math import detect_arbitrage, calculate_implied_probability
from ..core.sizing import calculate_stakes
from ..core.fees import get_venue_fees, calculate_total_fees
from ..utils.odds import decimal_to_american, format_american_odds
from ..utils.time import estimate_expiry_seconds
from ..config import MIN_ARBITRAGE_PROFIT_PCT, DEFAULT_STAKE_USD


def find_arbitrage_opportunities(
    event_groups: dict[str, list[Market]],
    min_profit_pct: float = MIN_ARBITRAGE_PROFIT_PCT,
    stake: float = DEFAULT_STAKE_USD
) -> list[Opportunity]:
    """
    Find arbitrage opportunities across markets.

    Examines markets from different venues for the same event
    to find profitable arbitrage situations.

    Args:
        event_groups: Markets grouped by event ID
        min_profit_pct: Minimum profit % to report
        stake: Total stake for calculations

    Returns:
        List of arbitrage opportunities
    """
    opportunities = []

    for event_id, markets in event_groups.items():
        if len(markets) < 2:
            continue

        # For same-event arb, we need outcomes from different venues
        # Extract all outcomes by name and venue
        outcomes_by_name: dict[str, list[Outcome]] = {}

        for market in markets:
            for outcome in market.outcomes:
                name = outcome.name.lower()
                if name not in outcomes_by_name:
                    outcomes_by_name[name] = []
                outcomes_by_name[name].append(outcome)

        # Need at least 2 outcomes with multiple venue options
        if len(outcomes_by_name) < 2:
            continue

        # Find best odds for each outcome
        best_odds: dict[str, tuple[Outcome, float]] = {}  # name -> (outcome, odds)

        for name, outcomes in outcomes_by_name.items():
            # Find best odds across venues
            best = max(outcomes, key=lambda x: x.odds_decimal)
            best_odds[name] = (best, best.odds_decimal)

        # Check if arb exists with best prices
        outcome_names = list(best_odds.keys())
        if len(outcome_names) < 2:
            continue

        # For binary markets
        if len(outcome_names) == 2:
            name1, name2 = outcome_names
            outcome1, odds1 = best_odds[name1]
            outcome2, odds2 = best_odds[name2]

            # Calculate fees
            venues = [outcome1.venue, outcome2.venue]
            fee_pct = sum(get_venue_fees(v).trading_fee_pct for v in venues)

            # Check arbitrage
            arb_result = detect_arbitrage([odds1, odds2], fee_pct)

            if arb_result.is_arbitrage and arb_result.profit_pct >= min_profit_pct:
                # Calculate stake sizing
                sizing = calculate_stakes([odds1, odds2], stake, fee_pct)

                # Generate instructions
                instructions = [
                    BetInstruction(
                        venue=outcome1.venue,
                        outcome=outcome1.name,
                        stake_usd=sizing.stakes[0],
                        odds_decimal=odds1,
                        odds_american=format_american_odds(decimal_to_american(odds1)),
                        potential_payout=round(sizing.stakes[0] * odds1, 2)
                    ),
                    BetInstruction(
                        venue=outcome2.venue,
                        outcome=outcome2.name,
                        stake_usd=sizing.stakes[1],
                        odds_decimal=odds2,
                        odds_american=format_american_odds(decimal_to_american(odds2)),
                        potential_payout=round(sizing.stakes[1] * odds2, 2)
                    )
                ]

                # Determine risk level
                risk = assess_risk(sizing.profit_pct, venues)

                # Estimate expiry
                timestamps = [o.timestamp for o in [outcome1, outcome2]]
                oldest = min(timestamps)
                expiry = estimate_expiry_seconds(oldest)

                # Get event info from first market
                market = markets[0]

                opportunities.append(Opportunity(
                    type="ARBITRAGE",
                    event_id=event_id,
                    event_name=market.event_name,
                    market_type=market.market_type,
                    expected_profit_pct=round(sizing.profit_pct, 4),
                    expected_profit_usd=sizing.guaranteed_profit,
                    total_stake=sizing.total_stake,
                    instructions=instructions,
                    fees_usd=round(sizing.total_stake * fee_pct / 100, 2),
                    risk=risk,
                    expires_in_seconds=expiry
                ))

        # For multi-outcome markets (3+ outcomes)
        elif len(outcome_names) >= 3:
            all_outcomes = [(name, best_odds[name][0], best_odds[name][1])
                           for name in outcome_names]
            all_odds = [o[2] for o in all_outcomes]

            # Calculate fees
            venues = [o[1].venue for o in all_outcomes]
            fee_pct = sum(get_venue_fees(v).trading_fee_pct for v in venues)

            # Check arbitrage
            arb_result = detect_arbitrage(all_odds, fee_pct)

            if arb_result.is_arbitrage and arb_result.profit_pct >= min_profit_pct:
                sizing = calculate_stakes(all_odds, stake, fee_pct)

                instructions = []
                for i, (name, outcome, odds) in enumerate(all_outcomes):
                    instructions.append(BetInstruction(
                        venue=outcome.venue,
                        outcome=outcome.name,
                        stake_usd=sizing.stakes[i],
                        odds_decimal=odds,
                        odds_american=format_american_odds(decimal_to_american(odds)),
                        potential_payout=round(sizing.stakes[i] * odds, 2)
                    ))

                risk = assess_risk(sizing.profit_pct, venues)
                market = markets[0]

                opportunities.append(Opportunity(
                    type="ARBITRAGE",
                    event_id=event_id,
                    event_name=market.event_name,
                    market_type=market.market_type,
                    expected_profit_pct=round(sizing.profit_pct, 4),
                    expected_profit_usd=sizing.guaranteed_profit,
                    total_stake=sizing.total_stake,
                    instructions=instructions,
                    fees_usd=round(sizing.total_stake * fee_pct / 100, 2),
                    risk=risk,
                    expires_in_seconds=30
                ))

    return opportunities


def assess_risk(
    profit_pct: float,
    venues: list[str]
) -> Literal["LOW", "MEDIUM", "HIGH"]:
    """
    Assess risk level of an arbitrage opportunity.

    Factors:
    - Profit margin (higher = safer)
    - Venue reliability
    - Number of legs
    """
    # Higher profit = lower execution risk
    if profit_pct >= 2.0:
        base_risk = "LOW"
    elif profit_pct >= 0.5:
        base_risk = "MEDIUM"
    else:
        base_risk = "HIGH"

    # Prediction markets are generally lower risk
    prediction_markets = {"polymarket", "kalshi", "manifold"}
    if all(v in prediction_markets for v in venues):
        return "LOW"

    # Cross-venue sportsbook has execution risk
    if len(set(venues)) > 1:
        if base_risk == "LOW":
            return "MEDIUM"

    return base_risk


def find_best_prices(
    event_groups: dict[str, list[Market]]
) -> list[Opportunity]:
    """
    Find best available prices for each outcome.

    Not arbitrage, but useful for showing where to get best odds.
    """
    # This would highlight dominant prices without arb
    # Implementation similar to above but without arb check
    return []
