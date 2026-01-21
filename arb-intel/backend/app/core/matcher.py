"""Market matching module.

Matches similar events across different platforms using fuzzy string matching
and entity extraction.
"""

import re
from difflib import SequenceMatcher
from typing import Optional
from ..core.models import Market


# Category normalization mapping
CATEGORY_GROUPS = {
    "politics": ["politics", "political", "election", "elections", "us-politics",
                 "government", "congress", "senate", "presidential", "vote", "voting",
                 "president", "governor", "mayor"],
    "sports": ["sports", "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
               "baseball", "hockey", "tennis", "golf", "mma", "ufc", "boxing",
               "champions-league", "premier-league", "world-cup", "super-bowl"],
    "crypto": ["crypto", "cryptocurrency", "bitcoin", "ethereum", "btc", "eth", "defi"],
    "tech": ["tech", "technology", "ai", "artificial-intelligence", "science", "space",
             "prediction"],  # "prediction" often used for tech/general markets
    "economics": ["economics", "economy", "finance", "financial", "stocks", "markets",
                  "fed", "federal-reserve", "inflation", "gdp"],
    "entertainment": ["entertainment", "movies", "tv", "music", "oscars", "awards"],
    "world": ["world", "international", "geopolitics", "war", "conflict"],
}


def normalize_category(category: str) -> str:
    """Normalize category to canonical form for cross-platform matching."""
    cat_lower = category.lower().replace("_", "-").replace(" ", "-")

    for canonical, variants in CATEGORY_GROUPS.items():
        for variant in variants:
            if variant in cat_lower or cat_lower in variant:
                return canonical

    # Default to "other" if no match
    return "other"


def categories_match(cat1: str, cat2: str) -> bool:
    """Check if two categories are compatible for matching."""
    norm1 = normalize_category(cat1)
    norm2 = normalize_category(cat2)

    # "tech" includes "prediction" which is a generic catch-all used by prediction markets
    # Allow it to match with politics since many political markets are under "prediction"
    prediction_matches = {"tech", "politics", "world", "economics"}
    if norm1 == "tech" or norm2 == "tech":
        return norm1 in prediction_matches and norm2 in prediction_matches

    # Require same normalized category for others
    return norm1 == norm2


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Lowercase
    text = text.lower()
    # Remove common prefixes
    text = re.sub(r'^(will |who will |what will |which )', '', text)
    # Remove punctuation except important chars
    text = re.sub(r'[^\w\s\d\-]', ' ', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def extract_entities(text: str) -> set[str]:
    """Extract key entities from market text."""
    entities = set()
    text_lower = text.lower()

    # Political figures
    politicians = [
        'trump', 'biden', 'vance', 'desantis', 'harris', 'obama',
        'pence', 'haley', 'ramaswamy', 'newsom', 'ocasio-cortez', 'aoc',
        'rubio', 'cruz', 'sanders', 'warren', 'pelosi', 'mcconnell',
        'buttigieg', 'booker', 'klobuchar', 'yang', 'gabbard'
    ]
    for p in politicians:
        if p in text_lower:
            entities.add(p)

    # Years
    years = re.findall(r'20\d{2}', text)
    entities.update(years)

    # Political terms
    political_terms = [
        'president', 'presidential', 'election', 'nomination', 'nominee',
        'republican', 'democrat', 'gop', 'dnc', 'rnc',
        'senate', 'house', 'congress', 'governor',
        'primary', 'caucus', 'midterm'
    ]
    for term in political_terms:
        if term in text_lower:
            entities.add(term)

    # Economic terms
    economic_terms = [
        'fed', 'federal reserve', 'interest rate', 'rates', 'bps',
        'inflation', 'gdp', 'recession', 'tariff'
    ]
    for term in economic_terms:
        if term in text_lower:
            entities.add(term.replace(' ', '_'))

    # Specific events
    events = [
        'super bowl', 'world series', 'nba finals', 'stanley cup',
        'oscars', 'grammy', 'emmy', 'golden globe',
        'greenland', 'ukraine', 'russia', 'china', 'taiwan'
    ]
    for event in events:
        if event in text_lower:
            entities.add(event.replace(' ', '_'))

    return entities


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity score between two texts."""
    # Normalize texts
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    # Direct string similarity
    string_sim = SequenceMatcher(None, norm1, norm2).ratio()

    # Entity overlap
    entities1 = extract_entities(text1)
    entities2 = extract_entities(text2)

    if entities1 and entities2:
        intersection = len(entities1 & entities2)
        union = len(entities1 | entities2)
        entity_sim = intersection / union if union > 0 else 0
    else:
        entity_sim = 0

    # Word overlap (Jaccard similarity)
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if words1 and words2:
        word_intersection = len(words1 & words2)
        word_union = len(words1 | words2)
        word_sim = word_intersection / word_union if word_union > 0 else 0
    else:
        word_sim = 0

    # Combined score (weighted)
    # Entity match is most important, then word overlap, then string similarity
    combined = (entity_sim * 0.5) + (word_sim * 0.3) + (string_sim * 0.2)

    return combined


def outcomes_compatible(market1: Market, market2: Market) -> bool:
    """Check if outcome types are compatible for arbitrage."""
    outcomes1 = {o.name.lower() for o in market1.outcomes}
    outcomes2 = {o.name.lower() for o in market2.outcomes}

    # Binary markets (Yes/No) - both must be binary
    binary_outcomes = {"yes", "no"}
    is_binary1 = outcomes1 <= binary_outcomes or outcomes1 == binary_outcomes
    is_binary2 = outcomes2 <= binary_outcomes or outcomes2 == binary_outcomes

    # If both are binary, they're compatible
    if is_binary1 and is_binary2:
        return True

    # If one is binary and other has specific names (candidates, teams), not compatible
    if is_binary1 != is_binary2:
        return False

    # Both have specific outcomes - check for overlap
    # At least one outcome name should match (partial is ok)
    for o1 in outcomes1:
        for o2 in outcomes2:
            # Check for substring match or exact match
            if o1 in o2 or o2 in o1:
                return True

    return False


def markets_match(market1: Market, market2: Market, threshold: float = 0.45) -> bool:
    """Check if two markets are about the same event."""
    # Don't match markets from the same venue
    venues1 = {o.venue for o in market1.outcomes}
    venues2 = {o.venue for o in market2.outcomes}
    if venues1 & venues2:
        return False

    # Require compatible category - critical to avoid cross-category matches
    if not categories_match(market1.sport, market2.sport):
        return False

    # Require compatible outcomes - Yes/No shouldn't match candidate names
    if not outcomes_compatible(market1, market2):
        return False

    # Calculate similarity
    sim = calculate_similarity(market1.event_name, market2.event_name)

    return sim >= threshold


def create_canonical_event_id(markets: list[Market]) -> str:
    """Create a canonical event ID for matched markets."""
    # Use the longest/most descriptive name
    best_name = max(markets, key=lambda m: len(m.event_name)).event_name
    # Normalize it
    normalized = normalize_text(best_name)
    # Create hash-like ID
    words = normalized.split()[:5]  # First 5 words
    return "matched_" + "_".join(words)


def find_matching_markets(
    markets: list[Market],
    threshold: float = 0.45
) -> dict[str, list[Market]]:
    """
    Group markets that are about the same event.

    Returns dict mapping canonical event ID to list of matched markets.
    """
    # First, group by original event_id (same-venue markets)
    groups: dict[str, list[Market]] = {}

    for market in markets:
        if market.event_id not in groups:
            groups[market.event_id] = []
        groups[market.event_id].append(market)

    # Now try to match markets across venues
    market_list = list(markets)
    matched_indices: set[int] = set()
    merged_groups: list[list[Market]] = []

    for i, market1 in enumerate(market_list):
        if i in matched_indices:
            continue

        current_group = [market1]
        matched_indices.add(i)

        for j, market2 in enumerate(market_list):
            if j in matched_indices:
                continue
            if j <= i:
                continue

            # Check if this market matches any in current group
            if any(markets_match(m, market2, threshold) for m in current_group):
                current_group.append(market2)
                matched_indices.add(j)

        if len(current_group) > 1:
            # Found cross-venue match
            merged_groups.append(current_group)

    # Create result dict
    result: dict[str, list[Market]] = {}

    # Add merged groups with new canonical IDs
    for group in merged_groups:
        venues = set()
        for m in group:
            for o in m.outcomes:
                venues.add(o.venue)

        # Only keep groups with multiple venues
        if len(venues) > 1:
            canonical_id = create_canonical_event_id(group)
            result[canonical_id] = group

    # Add single-venue groups (original event_ids)
    for event_id, group in groups.items():
        # Check if already in a merged group
        group_markets_ids = {id(m) for m in group}
        already_merged = False
        for merged in merged_groups:
            merged_ids = {id(m) for m in merged}
            if group_markets_ids & merged_ids:
                already_merged = True
                break

        if not already_merged:
            result[event_id] = group

    return result


def get_match_details(market1: Market, market2: Market) -> dict:
    """Get detailed match information for debugging."""
    sim = calculate_similarity(market1.event_name, market2.event_name)
    entities1 = extract_entities(market1.event_name)
    entities2 = extract_entities(market2.event_name)

    return {
        "market1": market1.event_name,
        "market2": market2.event_name,
        "similarity": round(sim, 3),
        "entities1": list(entities1),
        "entities2": list(entities2),
        "shared_entities": list(entities1 & entities2),
        "is_match": sim >= 0.4
    }
