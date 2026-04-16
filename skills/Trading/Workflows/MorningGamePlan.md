---
description: Build the daily morning game plan with market data, intelligence, and Notion integration
---

# MorningGamePlan Workflow

## Steps

### Phase 1: Market Context (6:00-6:15 CT)

1. **Check futures/ETFs:**
   - `MarketData.ts quote SPY QQQ IWM /CL GLD`
   - Assess overnight direction and gap

2. **Economic calendar:**
   - Check for FOMC, CPI, jobs, GDP, or other scheduled releases
   - Flag any events that could cause volatility

3. **Determine market regime:**
   - Trending / Ranging / Gap Day / High Volatility / Choppy
   - Query intelligence: `Intelligence/MarketRegimes/[regime].md` for how to trade today

### Phase 2: Scanning & Watchlist (6:15-6:45 CT)

1. **Run Finviz screener:**
   - Pre-market gappers > 3% with volume > 500K
   - Unusual volume movers
   - Earnings/catalyst plays

2. **For each candidate ticker:**
   - `MarketData.ts quote TICKER` — fundamentals snapshot
   - `MarketData.ts ohlcv TICKER --period daily --range 5d` — calculate Camarilla pivots
   - `EdgarLookup.ts filings TICKER --days 14` — recent SEC filings
   - Extract catalyst keywords from filings

3. **Grade each ticker** (per PlaybookSetups.md grading criteria)

4. **Separate into two categories:**
   - **Fresh News:** New catalysts today (earnings, filings, breaking news)
   - **Second Day Plays / Technical Setups:** Day 2 continuations, HTF setups, range breaks

### Phase 3: Query Intelligence Base (6:45-7:00 CT)

For each ticker on the watchlist:

1. **Match to playbook setup:**
   - Search `Intelligence/Setups/` for matching patterns
   - Pull relevant analyst insights for this setup type

2. **Check analyst commentary:**
   - Search `Intelligence/Analysts/` for any recent mentions of ticker or sector

3. **Load relevant psychology reminders:**
   - Based on recent review patterns (e.g., "exiting winners too early")
   - Pull from `Intelligence/Psychology/`

### Phase 4: Build the Game Plan (7:00-7:15 CT)

1. **Create Notion entry** in Daily Game Plan database:
   - Date, Monthly Goal, Weekly Goal
   - Market Regime
   - 1% Change (behavioral focus from recent lessons)

2. **Populate Fresh News sub-database:**
   - Ticker, Support (Camarilla S3/S4), Resistance (Camarilla R3/R4)
   - Inflexion point, Bias, Setup type, Trading Plan, Notes

3. **Populate Second Day Plays sub-database:**
   - Same fields, focused on continuation and technical patterns

4. **Each Trading Plan field should include:**
   - Entry trigger (specific price action confirmation)
   - Stop loss (ATR-based or level-based)
   - Profit targets (R:R ratio)
   - Intelligence note (what analysts/intel says about this setup)

### Phase 5: Identify the Thesis Trade (7:15-7:30 CT)

> "Trade the thesis, not the ticker that's moving the most on your screen."

1. **Which ticker has the highest conviction?**
   - Strongest catalyst + cleanest chart + best setup grade
   - Intelligence base confirms edge in this setup type

2. **Mark as PRIMARY TRADE:**
   - This gets live capital
   - Define exact entry, stop, targets
   - Plan to size into conviction (not 5-share lots)

3. **Prepare both directions:**
   - Long scenario AND short scenario for the primary ticker

### Phase 6: Output Summary

Present the complete game plan:
```
═══ MORNING GAME PLAN — [Date] ═══

Market Regime: [regime]
1% Change: [behavioral focus]
Thesis Trade: [TICKER] — [setup type] — [direction]

FRESH NEWS:
[table of tickers with levels, bias, plan]

SECOND DAY PLAYS:
[table of tickers with levels, bias, plan]

INTELLIGENCE NOTES:
[relevant analyst insights for today's setups]

RULES REMINDER:
[top 3 rules from RulesOfEngagement.md based on recent patterns]
```
