---
description: Generate annotated daily report card with grades and pattern analysis
---

# DailyReview Workflow

**Depends on:** IngestTrades (run first if not already done)

## Steps

### 1. Ingest Trades

If trades haven't been ingested for today, run the IngestTrades workflow first.

### 2. Grade Each Ticker

For each ticker traded, evaluate:

| Criteria | Weight | Description |
|----------|--------|-------------|
| Setup quality | High | Was this a playbook setup? |
| Entry precision | High | Entry at planned level with confirmation? |
| Stop discipline | High | Was stop honored? Any averaging down? |
| Exit quality | Medium | Let winners run or cut too early? |
| Size appropriateness | Medium | Conviction sizing or scattered small lots? |
| Overtrading | High | How many executions vs. necessary? |

**Grading Scale:**
- **A**: Clean playbook trade, precise entry/exit, disciplined
- **B**: Right idea, good execution with minor issues
- **C**: Right direction but poor execution (churning, early exits)
- **D**: Wrong thesis or major discipline violation
- **F**: Revenge trade, averaging down, no plan

### 3. Identify Patterns

Check against known behavioral patterns from TELOS and intelligence base:
- Revenge trading (grinding same ticker after losses)
- Averaging down into losers
- Inverse allocation (best trades in sim, worst in live)
- Exiting winners too early
- Overtrading (too many executions for the P&L)
- Trading outside the game plan

### 4. Calculate Discipline Score

Score 1-10 based on:
- Followed morning game plan? (+2)
- Playbook trades only? (+2)
- Honored stops? (+2)
- No revenge trading? (+1)
- Paused after losses? (+1)
- Thesis trade taken live? (+1)
- Appropriate sizing? (+1)

### 5. Compare to Prior Days

Load recent reviews from `~/.claude/PAI/USER/TRADING/Reviews/` and show trend:
```
Date | Live P&L | Sim P&L | Discipline | Key Pattern
```

### 6. Extract Lessons

Identify 1-2 actionable lessons. Format for potential TELOS update.

### 7. Output Format

```
## Daily Report Card — [Date]

### P&L Summary
[Table]

### Trade-by-Trade Review
[Per ticker: timeline, chart, grade, verdict]

### Patterns Identified
[Behavioral patterns observed]

### Discipline Score: X/10
[Breakdown]

### Multi-Day Trend
[Table]

### Lessons
[1-2 actionable takeaways]
```
