from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class Outcome(BaseModel):
    """Single outcome with odds from a specific venue."""
    name: str
    odds_decimal: float = Field(gt=1.0, description="Decimal odds must be > 1")
    venue: str
    liquidity: float | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Market(BaseModel):
    """Canonical market representation with outcomes from multiple venues."""
    event_id: str
    sport: str
    event_name: str
    market_type: str  # moneyline, spread, total, prop
    outcomes: list[Outcome]
    start_time: datetime | None = None


class VenueFees(BaseModel):
    """Fee structure for a betting venue."""
    venue: str
    trading_fee_pct: float = 0.0  # Percentage fee on trade
    settlement_fee: float = 0.0   # Fixed fee on settlement
    withdrawal_fee: float = 0.0   # Fee to withdraw funds


class BetInstruction(BaseModel):
    """Human-readable bet instruction."""
    venue: str
    outcome: str
    stake_usd: float
    odds_decimal: float
    odds_american: str
    potential_payout: float


class Opportunity(BaseModel):
    """Detected arbitrage or +EV opportunity."""
    type: Literal["ARBITRAGE", "EV", "BEST_PRICE"]
    event_id: str
    event_name: str
    market_type: str
    expected_profit_pct: float
    expected_profit_usd: float
    total_stake: float
    instructions: list[BetInstruction]
    fees_usd: float
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    expires_in_seconds: int
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class ScanResult(BaseModel):
    """Result of a scan cycle."""
    opportunities: list[Opportunity]
    markets_scanned: int
    scan_duration_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
