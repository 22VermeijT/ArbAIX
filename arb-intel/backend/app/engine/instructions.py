"""Human-readable instruction generation.

Converts opportunities into clear, actionable step-by-step instructions
that humans can execute manually.

Output must be:
- Exact bet amounts
- Clear venue names
- Specific odds
- Expected outcomes
"""

from ..core.models import Opportunity, BetInstruction


def format_opportunity(opp: Opportunity) -> str:
    """
    Format an opportunity as human-readable instructions.

    Example output:
    ```
    ARBITRAGE OPPORTUNITY - NBA: Lakers vs Celtics
    Expected Profit: $11.23 (0.48%)
    Risk: LOW | Expires in ~45 seconds

    INSTRUCTIONS:
    1. Bet $238.17 on Lakers ML at DraftKings (+110)
    2. Bet $250.00 on Celtics ML at FanDuel (+105)

    Total Stake: $488.17
    Guaranteed Payout: $499.40
    Fees: $0.00
    ```
    """
    lines = []

    # Header
    opp_type = opp.type.replace("_", " ")
    lines.append(f"{opp_type} OPPORTUNITY - {opp.event_name}")
    lines.append(f"Market: {opp.market_type.title()}")
    lines.append("")

    # Profit summary
    if opp.type == "ARBITRAGE":
        lines.append(f"Guaranteed Profit: ${opp.expected_profit_usd:.2f} ({opp.expected_profit_pct:.2f}%)")
    else:
        lines.append(f"Expected Value: ${opp.expected_profit_usd:.2f} ({opp.expected_profit_pct:.2f}%)")

    lines.append(f"Risk: {opp.risk} | Expires in ~{opp.expires_in_seconds} seconds")
    lines.append("")

    # Instructions
    lines.append("INSTRUCTIONS:")
    for i, inst in enumerate(opp.instructions, 1):
        lines.append(format_instruction(inst, i))

    lines.append("")

    # Summary
    lines.append(f"Total Stake: ${opp.total_stake:.2f}")

    if opp.type == "ARBITRAGE":
        # Calculate guaranteed payout
        payout = opp.total_stake + opp.expected_profit_usd + opp.fees_usd
        lines.append(f"Guaranteed Payout: ${payout:.2f}")

    if opp.fees_usd > 0:
        lines.append(f"Fees: ${opp.fees_usd:.2f}")

    return "\n".join(lines)


def format_instruction(inst: BetInstruction, step_num: int) -> str:
    """
    Format a single bet instruction.

    Example: "1. Bet $238.17 on Lakers ML at DraftKings (+110)"
    """
    venue_display = inst.venue.title().replace("_", " ")

    return (
        f"{step_num}. Bet ${inst.stake_usd:.2f} on {inst.outcome} "
        f"at {venue_display} ({inst.odds_american})"
    )


def format_opportunity_short(opp: Opportunity) -> str:
    """
    Format opportunity as single-line summary.

    Example: "ARB +0.48% | Lakers vs Celtics | DraftKings/FanDuel"
    """
    venues = "/".join(set(i.venue.title() for i in opp.instructions))
    return f"{opp.type[:3]} +{opp.expected_profit_pct:.2f}% | {opp.event_name} | {venues}"


def format_opportunity_json(opp: Opportunity) -> dict:
    """
    Format opportunity as JSON-serializable dict.

    Used for API responses and WebSocket messages.
    """
    return {
        "type": opp.type,
        "event_id": opp.event_id,
        "event_name": opp.event_name,
        "market_type": opp.market_type,
        "profit_pct": opp.expected_profit_pct,
        "profit_usd": opp.expected_profit_usd,
        "total_stake": opp.total_stake,
        "fees_usd": opp.fees_usd,
        "risk": opp.risk,
        "expires_in_seconds": opp.expires_in_seconds,
        "detected_at": opp.detected_at.isoformat(),
        "instructions": [
            {
                "step": i + 1,
                "venue": inst.venue,
                "outcome": inst.outcome,
                "stake_usd": inst.stake_usd,
                "odds_decimal": inst.odds_decimal,
                "odds_american": inst.odds_american,
                "potential_payout": inst.potential_payout,
            }
            for i, inst in enumerate(opp.instructions)
        ],
        "formatted_text": format_opportunity(opp),
    }


def format_opportunities_table(opportunities: list[Opportunity]) -> str:
    """
    Format multiple opportunities as ASCII table.

    For CLI output.
    """
    if not opportunities:
        return "No opportunities found."

    lines = []
    header = f"{'Type':<5} {'Profit':<8} {'Event':<40} {'Risk':<6} {'Venues'}"
    lines.append(header)
    lines.append("-" * len(header))

    for opp in opportunities[:20]:  # Limit to 20
        venues = "/".join(set(i.venue[:10] for i in opp.instructions))
        event = opp.event_name[:38] + ".." if len(opp.event_name) > 40 else opp.event_name
        line = f"{opp.type[:3]:<5} {opp.expected_profit_pct:>6.2f}% {event:<40} {opp.risk:<6} {venues}"
        lines.append(line)

    return "\n".join(lines)


def generate_disclaimer() -> str:
    """
    Generate advisory disclaimer text.

    MUST be displayed on all outputs.
    """
    return """
DISCLAIMER: This is advisory information only. No bets are placed automatically.
All betting decisions and executions must be made by you. Past opportunities
do not guarantee future results. Odds can change rapidly. Always verify
current odds before placing any bets. Gamble responsibly.
""".strip()
