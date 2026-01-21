"""Market and team name normalization.

Normalizes team names, market types, and event identifiers
across different data sources for canonical matching.
"""

import re
from datetime import datetime

# Common team name aliases (expand as needed)
TEAM_ALIASES: dict[str, str] = {
    # NBA
    "la lakers": "Los Angeles Lakers",
    "lakers": "Los Angeles Lakers",
    "lac": "Los Angeles Clippers",
    "la clippers": "Los Angeles Clippers",
    "clippers": "Los Angeles Clippers",
    "boston": "Boston Celtics",
    "celtics": "Boston Celtics",
    "gsw": "Golden State Warriors",
    "golden state": "Golden State Warriors",
    "warriors": "Golden State Warriors",
    "ny knicks": "New York Knicks",
    "knicks": "New York Knicks",
    "phx": "Phoenix Suns",
    "phoenix": "Phoenix Suns",
    "suns": "Phoenix Suns",
    # NFL
    "kc": "Kansas City Chiefs",
    "kansas city": "Kansas City Chiefs",
    "chiefs": "Kansas City Chiefs",
    "sf": "San Francisco 49ers",
    "san francisco": "San Francisco 49ers",
    "49ers": "San Francisco 49ers",
    "niners": "San Francisco 49ers",
    # Add more as needed
}

MARKET_TYPE_ALIASES: dict[str, str] = {
    "ml": "moneyline",
    "money line": "moneyline",
    "h2h": "moneyline",
    "head to head": "moneyline",
    "spread": "spread",
    "ats": "spread",
    "point spread": "spread",
    "handicap": "spread",
    "total": "total",
    "ou": "total",
    "over/under": "total",
    "over under": "total",
    "prop": "prop",
    "player prop": "prop",
}


def normalize_team_name(name: str) -> str:
    """
    Normalize team name to canonical form.

    Examples:
        "lakers" → "Los Angeles Lakers"
        "LA Lakers" → "Los Angeles Lakers"
        "Boston" → "Boston Celtics"
    """
    if not name:
        return name

    # Clean and lowercase for lookup
    cleaned = name.strip().lower()
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Check aliases
    if cleaned in TEAM_ALIASES:
        return TEAM_ALIASES[cleaned]

    # Return original with title case if no alias found
    return name.strip().title()


def normalize_market_type(market_type: str) -> str:
    """
    Normalize market type to canonical form.

    Examples:
        "ML" → "moneyline"
        "h2h" → "moneyline"
        "spread" → "spread"
        "O/U" → "total"
    """
    if not market_type:
        return "unknown"

    cleaned = market_type.strip().lower()
    cleaned = re.sub(r'[/\\]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    if cleaned in MARKET_TYPE_ALIASES:
        return MARKET_TYPE_ALIASES[cleaned]

    return cleaned


def generate_event_id(
    sport: str,
    team1: str,
    team2: str,
    date: datetime | None = None
) -> str:
    """
    Generate canonical event ID.

    Format: {sport}_{team1}_vs_{team2}_{YYYY_MM_DD}

    Teams are sorted alphabetically for consistency.

    Examples:
        "nba_boston_celtics_vs_los_angeles_lakers_2026_01_20"
    """
    # Normalize sport
    sport_clean = sport.strip().lower().replace(" ", "_")

    # Normalize and sort teams
    t1 = normalize_team_name(team1).lower().replace(" ", "_")
    t2 = normalize_team_name(team2).lower().replace(" ", "_")
    teams_sorted = sorted([t1, t2])

    # Add date if provided
    if date:
        date_str = date.strftime("%Y_%m_%d")
        return f"{sport_clean}_{teams_sorted[0]}_vs_{teams_sorted[1]}_{date_str}"

    return f"{sport_clean}_{teams_sorted[0]}_vs_{teams_sorted[1]}"


def normalize_outcome_name(outcome: str, market_type: str = "moneyline") -> str:
    """
    Normalize outcome name based on market type.

    Examples:
        "Lakers -3.5" with spread → "Los Angeles Lakers -3.5"
        "Over 220.5" with total → "Over 220.5"
    """
    if not outcome:
        return outcome

    outcome = outcome.strip()

    # Handle total markets
    if market_type == "total":
        outcome_lower = outcome.lower()
        if outcome_lower.startswith("over") or outcome_lower.startswith("o "):
            return "Over" + outcome[outcome_lower.find("over") + 4:]
        if outcome_lower.startswith("under") or outcome_lower.startswith("u "):
            return "Under" + outcome[outcome_lower.find("under") + 5:]
        return outcome

    # Handle spreads - extract team name and line
    if market_type == "spread":
        match = re.match(r'^(.+?)\s*([-+]?\d+\.?\d*)$', outcome)
        if match:
            team = normalize_team_name(match.group(1))
            line = match.group(2)
            return f"{team} {line}"

    # Default: normalize as team name
    return normalize_team_name(outcome)
