# Data Sources

## Finviz API
- **Purpose:** Screener, fundamentals, technicals snapshot
- **Key endpoints:**
  - Quote snapshot: fundamentals + technicals for a ticker
  - Screener: filter by gap%, volume, price, float, sector
- **Key fields:** Price, ATR, Float, Short%, Sector, 52W Range, RSI, Relative Volume, Market Cap, Avg Volume
- **API key location:** `~/.claude/PAI/USER/SKILLCUSTOMIZATIONS/Trading/PREFERENCES.md`

## Massive.com API
- **Purpose:** OHLCV historical candle data
- **Key endpoints:**
  - Daily candles: for Camarilla pivot calculation, support/resistance
  - Intraday candles (1min, 5min): for pattern analysis
- **Key fields:** Open, High, Low, Close, Volume per period
- **Used for:** Camarilla pivot calculation, ATR computation, trend identification
- **API key location:** `~/.claude/PAI/USER/SKILLCUSTOMIZATIONS/Trading/PREFERENCES.md`

## SEC EDGAR
- **Purpose:** Company filings for catalyst identification
- **Base URL:** `https://efts.sec.gov/LATEST/`
- **No API key required** (rate limit: 10 req/sec with User-Agent header)
- **Key filing types:**
  - 8-K: Material events (earnings, acquisitions, leadership changes, offerings)
  - 10-Q: Quarterly financials
  - 10-K: Annual financials
  - S-1: IPO registration
  - SC 13D/G: Institutional ownership changes
  - 4: Insider transactions
- **Catalyst keywords:** acquisition, merger, partnership, offering, FDA, approval, contract, restructuring, bankruptcy, investigation

## DAS Trader Exports
- **Path:** `/path/to/your/Trade_Review/
- **Files:**
  - `Trades.csv` — Individual executions (TradeID, Account, B/S, Symbol, Qty, Price, Time)
  - `Orders.csv` — Order history
  - `Tickets.csv` — Ticket data
  - `pnl-by-position-*.csv` — P&L summary by position
  - `pnl-by-position-*.jpg` — P&L screenshot
  - `positions-*.csv` — Position details
  - `*.jpg` — Chart screenshots per ticker
- **Accounts:** YOUR_LIVE_ACCOUNT (live), YOUR_SIM_ACCOUNT (sim)
