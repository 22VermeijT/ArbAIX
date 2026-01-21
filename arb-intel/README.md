# Arbitrage Intelligence Platform

Cross-market arbitrage and odds intelligence system for sports betting and prediction markets.

**ADVISORY-ONLY**: This system provides information only. No bets are placed automatically. All betting decisions and executions must be made by humans.

## Features

- Real-time odds aggregation from multiple sources
- Arbitrage opportunity detection
- +EV (Expected Value) signal detection
- Stake sizing calculations
- Human-readable bet instructions
- Live WebSocket updates
- Filtering and sorting

## Tech Stack

### Backend
- Python 3.11+
- FastAPI (async, high-performance)
- asyncio + aiohttp for concurrency
- Pydantic for strict schemas
- In-memory caching

### Frontend
- React + Vite
- TypeScript
- Tailwind CSS
- WebSockets for live updates

## Data Sources

| Source | Type | Status |
|--------|------|--------|
| Polymarket | Prediction Market | Ready |
| Kalshi | Prediction Market | Ready |
| Manifold Markets | Probability Anchor | Ready |
| Betfair | Betting Exchange | Requires API Key |
| The Odds API | Sportsbook Aggregator | Requires API Key |

## Project Structure

```
arb-intel/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # API key placeholders & settings
│   │   ├── core/
│   │   │   ├── models.py        # Pydantic data models
│   │   │   ├── normalization.py # Market normalization
│   │   │   ├── fees.py          # Fee models
│   │   │   ├── math.py          # Arbitrage & EV formulas
│   │   │   └── sizing.py        # Stake sizing
│   │   ├── ingestion/
│   │   │   ├── polymarket.py    # Polymarket client
│   │   │   ├── kalshi.py        # Kalshi client
│   │   │   ├── manifold.py      # Manifold client
│   │   │   ├── betfair.py       # Betfair client
│   │   │   └── sportsbooks.py   # Aggregator client
│   │   ├── engine/
│   │   │   ├── scanner.py       # Scan orchestrator
│   │   │   ├── arbitrage.py     # Arb detection
│   │   │   ├── ev.py            # +EV detection
│   │   │   └── instructions.py  # Output formatting
│   │   ├── api/
│   │   │   ├── routes.py        # REST endpoints
│   │   │   └── websocket.py     # WebSocket handler
│   │   └── utils/
│   │       ├── odds.py          # Odds conversions
│   │       ├── cache.py         # In-memory cache
│   │       └── time.py          # Time utilities
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main component
│   │   ├── api.ts               # API client
│   │   ├── types.ts             # TypeScript types
│   │   └── components/
│   │       ├── OpportunityTable.tsx
│   │       ├── OpportunityCard.tsx
│   │       ├── Filters.tsx
│   │       └── Disclaimer.tsx
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Quick Start

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/` | GET | Health check |
| `/api/opportunities` | GET | List opportunities with filters |
| `/api/opportunities/{id}` | GET | Get opportunity detail |
| `/api/scan` | POST | Trigger manual scan |
| `/api/markets` | GET | List cached markets |
| `/api/stats` | GET | Scanner statistics |
| `/ws` | WebSocket | Real-time updates |

### Query Parameters

- `type`: ARBITRAGE, EV, or all
- `min_profit`: Minimum profit percentage
- `risk`: LOW, MEDIUM, HIGH, or all
- `sport`: Filter by sport/category
- `limit`: Max results (default 50)

## Core Formulas

### Odds Conversion

```
American → Decimal:
  if odds > 0: decimal = 1 + odds / 100
  if odds < 0: decimal = 1 + 100 / abs(odds)

Decimal → Probability:
  probability = 1 / decimal
```

### Arbitrage Detection

```
Arbitrage Condition:
  P₁ + P₂ < 1 - total_fees

  Where: Pᵢ = 1 / decimal_oddsᵢ

Profit %:
  profit_pct = (1 - (P₁ + P₂ + fees)) × 100
```

### Stake Sizing

```
Given total capital C:
  stake₁ = (C × P₂) / (P₁ + P₂)
  stake₂ = (C × P₁) / (P₁ + P₂)

Guaranteed Cashout:
  cashout = stake₁ × decimal₁ = stake₂ × decimal₂

Guaranteed Profit:
  profit = cashout - C - fees
```

### Expected Value

```
EV = (P_true × payout) - stake - fees
EV% = ((P_true × decimal_odds) - 1 - fee%) × 100
```

## Configuration

Edit `backend/app/config.py` to add API keys:

```python
POLYMARKET_API_KEY = "your_key_here"
KALSHI_API_KEY = "your_key_here"
MANIFOLD_API_KEY = "your_key_here"
BETFAIR_API_KEY = "your_key_here"

# The Odds API - Free tier available at https://the-odds-api.com/
# Add to backend/app/ingestion/sportsbooks.py
ODDS_API_KEY = "your_key_here"
```

## What This System Does NOT Do

- Place bets automatically
- Store user credentials
- Manage sportsbook accounts
- Guarantee profits
- Use paid APIs (free tier only)

## Disclaimer

This system is for educational and informational purposes only. It does not constitute financial advice. All betting decisions and executions must be made by you. Odds can change rapidly. Always verify current odds before placing any bets. Gamble responsibly.

## License

MIT
