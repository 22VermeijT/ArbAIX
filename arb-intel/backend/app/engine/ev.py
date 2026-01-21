"""+EV (Positive Expected Value) detection.

Identifies bets with positive expected value by comparing
offered odds against estimated true probabilities.

Uses prediction markets (Polymarket, Manifold) as probability anchors.

EV = (P_true * payout) - stake - fees
EV% = ((P_true * decimal_odds) - 1) * 100
"""

from ..core.models import Market, Outcome, Opportunity, BetInstruction
from ..core.math import calculate_ev_pct, calculate_kelly_fraction
from ..core.fees import get_venue_fees
from ..utils.odds import decimal_to_american, format_american_odds, decimal_to_probability
from ..utils.time import estimate_expiry_seconds
from ..config import MIN_EV_PCT, DEFAULT_STAKE_USD


# Sources considered reliable probability anchors
PROBABILITY_ANCHORS = {"polymarket", "kalshi", "manifold", "betfair"}


def find_ev_opportunities(
    event_groups: dict[str, list[Market]],
    min_ev_pct: float = MIN_EV_PCT,
    stake: float = DEFAULT_STAKE_USD
) -> list[Opportunity]:
    """
    Find +EV opportunities using prediction markets as anchors.

    Compares sportsbook odds against prediction market probabilities
    to find positive expected value bets.

    Args:
        event_groups: Markets grouped by event ID
        min_ev_pct: Minimum EV% to report
        stake: Stake for calculations

    Returns:
        List of +EV opportunities
    """
    opportunities = []

    for event_id, markets in event_groups.items():
        # Separate anchor markets from betting markets
        anchor_markets = [m for m in markets if m.outcomes[0].venue in PROBABILITY_ANCHORS]
        betting_markets = [m for m in markets if m.outcomes[0].venue not in PROBABILITY_ANCHORS]

        if not anchor_markets or not betting_markets:
            continue

        # Use first anchor as probability source
        anchor = anchor_markets[0]

        # Build probability map from anchor
        true_probs: dict[str, float] = {}
        for outcome in anchor.outcomes:
            prob = decimal_to_probability(outcome.odds_decimal)
            true_probs[outcome.name.lower()] = prob

        # Check each betting market for +EV
        for market in betting_markets:
            for outcome in market.outcomes:
                outcome_name = outcome.name.lower()

                # Find matching anchor probability
                true_prob = true_probs.get(outcome_name)
                if true_prob is None:
                    continue

                # Get venue fees
                fee_pct = get_venue_fees(outcome.venue).trading_fee_pct

                # Calculate EV
                ev_pct = calculate_ev_pct(
                    outcome.odds_decimal,
                    true_prob,
                    fee_pct
                )

                if ev_pct >= min_ev_pct:
                    # Calculate Kelly sizing (fractional for safety)
                    kelly = calculate_kelly_fraction(
                        outcome.odds_decimal,
                        true_prob,
                        fee_pct
                    )
                    # Use quarter Kelly for conservative sizing
                    recommended_stake = min(stake, stake * kelly * 0.25)
                    recommended_stake = round(recommended_stake, 2)

                    # Build instruction
                    instruction = BetInstruction(
                        venue=outcome.venue,
                        outcome=outcome.name,
                        stake_usd=recommended_stake,
                        odds_decimal=outcome.odds_decimal,
                        odds_american=format_american_odds(
                            decimal_to_american(outcome.odds_decimal)
                        ),
                        potential_payout=round(
                            recommended_stake * outcome.odds_decimal, 2
                        )
                    )

                    # Calculate expected profit
                    expected_profit = recommended_stake * (ev_pct / 100)

                    # Determine risk (EV bets are inherently higher risk)
                    risk = "MEDIUM" if ev_pct >= 5.0 else "HIGH"

                    # Estimate expiry
                    expiry = estimate_expiry_seconds(outcome.timestamp)

                    opportunities.append(Opportunity(
                        type="EV",
                        event_id=event_id,
                        event_name=market.event_name,
                        market_type=market.market_type,
                        expected_profit_pct=round(ev_pct, 4),
                        expected_profit_usd=round(expected_profit, 2),
                        total_stake=recommended_stake,
                        instructions=[instruction],
                        fees_usd=round(recommended_stake * fee_pct / 100, 2),
                        risk=risk,
                        expires_in_seconds=expiry
                    ))

    return opportunities


def calculate_edge(
    offered_odds: float,
    anchor_odds: float,
    fee_pct: float = 0.0
) -> float:
    """
    Calculate edge (advantage) of offered odds vs anchor.

    Edge = offered_odds / anchor_odds - 1

    Positive edge means offered odds are better than fair.
    """
    true_prob = decimal_to_probability(anchor_odds)
    ev_pct = calculate_ev_pct(offered_odds, true_prob, fee_pct)
    return ev_pct


def find_cross_market_ev(
    event_groups: dict[str, list[Market]],
    min_edge_pct: float = 3.0
) -> list[tuple[Market, Market, float]]:
    """
    Find opportunities where one market's odds imply edge on another.

    Useful for comparing prediction market odds across platforms.

    Returns:
        List of (market1, market2, edge_pct) tuples
    """
    results = []

    for event_id, markets in event_groups.items():
        if len(markets) < 2:
            continue

        # Compare each pair of markets
        for i, m1 in enumerate(markets):
            for m2 in markets[i + 1:]:
                # Compare same outcomes
                for o1 in m1.outcomes:
                    for o2 in m2.outcomes:
                        if o1.name.lower() != o2.name.lower():
                            continue

                        # Calculate edge each direction
                        edge1 = calculate_edge(o1.odds_decimal, o2.odds_decimal)
                        edge2 = calculate_edge(o2.odds_decimal, o1.odds_decimal)

                        if edge1 >= min_edge_pct:
                            results.append((m1, m2, edge1))
                        if edge2 >= min_edge_pct:
                            results.append((m2, m1, edge2))

    return results
