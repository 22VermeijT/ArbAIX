// Shared TypeScript types

export interface BetInstruction {
  step: number;
  venue: string;
  outcome: string;
  stake_usd: number;
  odds_decimal: number;
  odds_american: string;
  potential_payout: number;
}

export interface Opportunity {
  type: 'ARBITRAGE' | 'EV' | 'BEST_PRICE';
  event_id: string;
  event_name: string;
  market_type: string;
  profit_pct: number;
  profit_usd: number;
  total_stake: number;
  fees_usd: number;
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  expires_in_seconds: number;
  detected_at: string;
  instructions: BetInstruction[];
  formatted_text: string;
}

export interface ScanResult {
  markets_scanned: number;
  opportunities_count: number;
  scan_duration_ms: number;
  timestamp: string;
  opportunities: Opportunity[];
}

export interface Stats {
  scanner_running: boolean;
  last_scan: string | null;
  total_markets: number;
  total_opportunities: number;
  arbitrage_count: number;
  ev_count: number;
  average_profit_pct: number;
  by_risk: {
    low: number;
    medium: number;
    high: number;
  };
}

export interface FilterState {
  type: 'all' | 'ARBITRAGE' | 'EV';
  minProfit: number;
  risk: 'all' | 'LOW' | 'MEDIUM' | 'HIGH';
  sport: string;
}

export interface WSMessage {
  type: string;
  timestamp?: string;
  opportunities?: Opportunity[];
  scanner_running?: boolean;
  opportunities_count?: number;
  disclaimer?: string;
  [key: string]: unknown;
}
