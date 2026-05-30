"""Daily USMetrics refresh → Notion canonical page.

Triggered by EventBridge Scheduler each morning. Fetches a curated subset of
US macro indicators from FRED + EIA, computes the headline deltas (latest
value, YoY change, week-over-week for weekly series), and updates the
Notion canonical page's properties (Doc name timestamp, Date, Description
of Content with "What changed" + "Why does that matter").

Body content is intentionally left untouched in this MVP — property updates
are the daily-visible signal. Full body refresh can be a later phase.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

LOG = logging.getLogger()
LOG.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FRED_API_KEY = os.environ["FRED_API_KEY"]
EIA_API_KEY = os.environ.get("EIA_API_KEY", "")
NOTION_TOKEN = os.environ["NOTION_INTEGRATION_TOKEN"]
NOTION_PAGE_ID = os.environ["NOTION_PAGE_ID"]
NOTION_VERSION = os.environ.get("NOTION_API_VERSION", "2022-06-28")

# Currated metric catalog. Mirrors what the local USMetrics skill highlights
# in its Executive Summary + Current Snapshot. Each entry: a FRED series ID,
# a human label, a units hint, and a freshness expectation (so we know
# whether to compute WoW vs MoM vs QoQ deltas).
@dataclass(frozen=True)
class Metric:
    series_id: str
    label: str
    units: str  # 'percent' | 'index' | 'currency' | 'millions' | 'billions' | 'thousands'
    cadence: str  # 'weekly' | 'monthly' | 'quarterly' | 'daily'
    higher_is_better: Optional[bool] = None  # for trend arrow direction


CATALOG: list[Metric] = [
    # Labor (most time-sensitive for daily refresh)
    Metric("UNRATE",   "Unemployment Rate (U-3)",     "percent",   "monthly",  False),
    Metric("ICSA",     "Initial Jobless Claims",      "thousands", "weekly",   False),
    Metric("PAYEMS",   "Nonfarm Payrolls",            "thousands", "monthly",  True),
    Metric("CIVPART",  "Labor Force Participation",   "percent",   "monthly",  True),
    Metric("CES0500000003", "Average Hourly Earnings", "currency", "monthly",  True),

    # Inflation
    Metric("CPIAUCSL", "CPI All Items",               "index",     "monthly",  None),
    Metric("CPILFESL", "Core CPI",                    "index",     "monthly",  None),
    Metric("PCEPILFE", "Core PCE",                    "index",     "monthly",  None),

    # Growth
    Metric("GDPC1",                "Real GDP",         "billions",  "quarterly", True),
    Metric("A191RL1Q225SBEA",      "GDP Growth Rate",  "percent",   "quarterly", True),
    Metric("INDPRO",               "Industrial Production", "index", "monthly", True),

    # Rates / Markets
    Metric("FEDFUNDS", "Fed Funds Rate",              "percent",   "monthly",  None),
    Metric("DGS10",    "10-Year Treasury",            "percent",   "daily",    None),
    Metric("DGS2",     "2-Year Treasury",             "percent",   "daily",    None),
    Metric("VIXCLS",   "VIX",                         "index",     "daily",    False),

    # Housing
    Metric("MORTGAGE30US", "30-Year Mortgage Rate",   "percent",   "weekly",   False),
    Metric("MSPUS",        "Median Home Price",       "currency",  "quarterly", None),

    # Consumer
    Metric("UMCSENT",  "Consumer Sentiment",          "index",     "monthly",  True),
    Metric("PSAVERT",  "Personal Saving Rate",        "percent",   "monthly",  True),
]


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — keeps Lambda zip tiny)
# ---------------------------------------------------------------------------


def http_get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "pai-usmetrics-refresh/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def notion_patch(path: str, body: dict, timeout: int = 15) -> dict:
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "pai-usmetrics-refresh/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# FRED fetch
# ---------------------------------------------------------------------------


def fred_observations(series_id: str, limit: int = 60) -> list[dict]:
    """Returns observations newest-first."""
    qs = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    })
    data = http_get_json(f"https://api.stlouisfed.org/fred/series/observations?{qs}")
    obs = data.get("observations", [])
    return [o for o in obs if o.get("value") not in (".", None, "")]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


@dataclass
class Snapshot:
    metric: Metric
    latest_value: float
    latest_date: str  # YYYY-MM-DD
    prior_value: Optional[float]  # immediately preceding observation
    prior_date: Optional[str]
    yoy_value: Optional[float]  # ~52 weeks / 12 months ago

    @property
    def pct_change_period(self) -> Optional[float]:
        if self.prior_value is None or self.prior_value == 0:
            return None
        return (self.latest_value - self.prior_value) / self.prior_value * 100

    @property
    def pct_change_yoy(self) -> Optional[float]:
        if self.yoy_value is None or self.yoy_value == 0:
            return None
        return (self.latest_value - self.yoy_value) / self.yoy_value * 100

    @property
    def abs_change_period(self) -> Optional[float]:
        if self.prior_value is None:
            return None
        return self.latest_value - self.prior_value


def take_snapshot(metric: Metric) -> Optional[Snapshot]:
    obs = fred_observations(metric.series_id, limit=70)
    if not obs:
        LOG.warning("no observations for %s", metric.series_id)
        return None
    latest = obs[0]
    prior = obs[1] if len(obs) > 1 else None
    # YoY index depends on cadence
    yoy_index = {"weekly": 52, "monthly": 12, "quarterly": 4, "daily": 252}.get(metric.cadence, 12)
    yoy = obs[yoy_index] if len(obs) > yoy_index else None
    return Snapshot(
        metric=metric,
        latest_value=float(latest["value"]),
        latest_date=latest["date"],
        prior_value=float(prior["value"]) if prior else None,
        prior_date=prior["date"] if prior else None,
        yoy_value=float(yoy["value"]) if yoy else None,
    )


# ---------------------------------------------------------------------------
# Callout generation: "What changed" + "Why does that matter"
# ---------------------------------------------------------------------------

# What-matters templates per series. Keeps editorial out of the data layer
# without fabricating opinions in the user's voice.
WHY_TEMPLATES: dict[str, str] = {
    "ICSA": (
        "Initial Jobless Claims is the highest-frequency leading indicator of "
        "labor health (weekly, Thursday 8:30 ET). A single move is noise; "
        "two or three consecutive in the same direction is the signal. "
        "Sustained rises tend to support Fed rate-cut narratives and move "
        "front-end Treasuries."
    ),
    "UNRATE": (
        "U-3 Unemployment Rate is the monthly headline labor number from BLS "
        "(first Friday of the month). It's a lagging indicator — by the time "
        "UNRATE moves, the trend is already in the higher-frequency series "
        "(claims, payrolls revisions)."
    ),
    "PAYEMS": (
        "Nonfarm Payrolls is the monthly net-change-in-jobs print. The "
        "headline gets attention, but the recent revisions to prior months "
        "are usually the more meaningful information."
    ),
    "CPIAUCSL": (
        "Headline CPI sets the inflation tape for markets and the Fed. The "
        "YoY change matters more than the MoM; sticky core (CPILFESL) is what "
        "the Fed actually targets."
    ),
    "FEDFUNDS": (
        "Effective Fed Funds Rate tracks the actual rate, which can deviate "
        "from the FOMC target band intra-month. Changes here lag FOMC meetings."
    ),
    "DGS10": (
        "10-Year Treasury yield is the price the bond market puts on growth + "
        "inflation expectations. Decoupling from Fed Funds (e.g. Fed cutting "
        "while 10Y rises) signals the market is repricing fiscal or inflation risk."
    ),
    "VIXCLS": (
        "VIX measures 30-day implied volatility on the S&P. It's a fear gauge: "
        "elevated VIX → option premiums rich, hedging expensive. Sub-15 readings "
        "are often complacency markers."
    ),
}


def format_value(snap: Snapshot) -> str:
    v = snap.latest_value
    u = snap.metric.units
    if u == "percent":     return f"{v:.1f}%"
    if u == "currency":    return f"${v:,.2f}"
    if u == "thousands":   return f"{v / 1000:.1f}K" if v >= 1000 else f"{v:.0f}"
    if u == "millions":    return f"{v / 1000:,.1f}M" if v >= 1000 else f"{v:.0f}M"
    if u == "billions":    return f"${v:,.1f}B"
    return f"{v:.2f}"


def what_changed(snaps: list[Snapshot]) -> Optional[Snapshot]:
    """Return the most-recently-updated weekly/daily snapshot that's moved."""
    # Prefer weekly cadence (claims, mortgage), since they update most often
    candidates = [s for s in snaps if s.metric.cadence in ("weekly", "daily") and s.abs_change_period not in (None, 0)]
    if not candidates:
        return None
    # Most recent observation date wins; tie-break by absolute % change
    candidates.sort(key=lambda s: (s.latest_date, abs(s.pct_change_period or 0)), reverse=True)
    return candidates[0]


def build_description(snaps: list[Snapshot]) -> str:
    """Single string for the Notion 'Description of Content' property.

    Notion description is plain text (no markdown rendering) so we keep it
    tight: headline values, then what-changed callout, then why-does-it-matter."""
    by_id = {s.metric.series_id: s for s in snaps}

    headline_keys = ["UNRATE", "ICSA", "CPIAUCSL", "GDPC1", "FEDFUNDS"]
    headline_parts = []
    for k in headline_keys:
        s = by_id.get(k)
        if s is None:
            continue
        if k == "CPIAUCSL" and s.pct_change_yoy is not None:
            headline_parts.append(f"CPI {s.pct_change_yoy:+.1f}% YoY")
        elif k == "GDPC1" and s.pct_change_yoy is not None:
            headline_parts.append(f"Real GDP {s.pct_change_yoy:+.1f}% YoY")
        elif k == "ICSA":
            headline_parts.append(f"Claims {format_value(s)} (week of {s.latest_date})")
        elif k == "UNRATE":
            headline_parts.append(f"U-3 {format_value(s)} ({s.latest_date[:7]})")
        elif k == "FEDFUNDS":
            headline_parts.append(f"Fed Funds {format_value(s)}")

    headline = "Headline: " + "; ".join(headline_parts) + "."

    changed = what_changed(snaps)
    if changed:
        delta = changed.abs_change_period or 0
        pct = changed.pct_change_period or 0
        sign = "+" if delta > 0 else ""
        what = (
            f"What changed: {changed.metric.label} printed {format_value(changed)} "
            f"({changed.latest_date}), {sign}{delta:.1f} ({sign}{pct:.1f}%) vs prior {changed.prior_date}."
        )
        why_tmpl = WHY_TEMPLATES.get(changed.metric.series_id)
        why = f"Why it matters: {why_tmpl}" if why_tmpl else ""
    else:
        what = "What changed: no new releases since previous refresh."
        why = ""

    parts = [headline, what, why]
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def handler(event, context):
    LOG.info("usmetrics refresh starting; event=%s", json.dumps(event or {})[:200])

    snaps: list[Snapshot] = []
    failures: list[str] = []
    for metric in CATALOG:
        try:
            snap = take_snapshot(metric)
            if snap is not None:
                snaps.append(snap)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{metric.series_id}: {exc}")
            LOG.warning("snapshot failed for %s: %s", metric.series_id, exc)

    if not snaps:
        LOG.error("no snapshots collected; aborting Notion update")
        return {"ok": False, "snapshots": 0, "failures": failures}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    description = build_description(snaps)
    # Notion description fields cap at 2000 chars — clip defensively.
    description = description[:1900]

    body = {
        "properties": {
            "Doc name": {"title": [{"text": {"content": "US Economic State Analysis"}}]},
            "Description of Content": {"rich_text": [{"text": {"content": description}}]},
            "Date": {"date": {"start": today}},
        }
    }
    notion_patch(f"/pages/{NOTION_PAGE_ID}", body)
    LOG.info("notion page updated; snapshots=%d failures=%d", len(snaps), len(failures))

    return {
        "ok": True,
        "snapshots": len(snaps),
        "failures": failures,
        "description_preview": description[:200],
    }
