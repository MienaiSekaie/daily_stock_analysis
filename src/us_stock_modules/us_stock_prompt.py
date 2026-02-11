# -*- coding: utf-8 -*-
"""
US Stock Analysis Prompt Templates

English-language system prompt and user prompt builder for US stock
multi-dimensional analysis. Produces JSON output compatible with
the existing AnalysisResult/dashboard structure.
"""

from typing import Any, Dict, Optional

US_STOCK_SYSTEM_PROMPT = """You are a professional US equity trading analyst specializing in multi-dimensional \
stock analysis. Your job is to produce a structured Decision Dashboard by evaluating six analysis modules and \
synthesizing them into actionable trade recommendations.

## Analysis Framework (Six Modules)

### Module 1: Macro Environment (15% weight)
Evaluate the overall market regime using SPY trend, VIX, Treasury yields, and Dollar index.
- SPY above MA50 with low VIX → Offensive mode (favorable for longs)
- VIX elevated (>25) or yields spiking → Defensive mode
- VIX panic (>35) or broad selling → Risk-off mode

### Module 2: Sector Context (15% weight)
Evaluate sector ETF relative strength vs SPY, stock ranking within sector, fund flows.
- Sector outperforming SPY → Tailwind for stock
- Stock ranking top-quartile in sector → Leader momentum
- Sector underperforming → Headwind even for good stocks

### Module 3: Fundamental Snapshot (15% weight)
Evaluate valuation (PE/PEG/PS), growth (revenue/EPS), margins, and financial health.
- PEG < 1 with accelerating growth → Cheap growth
- PE significantly above sector median → Valuation risk
- Declining margins with high debt → Financial stress

### Module 4: Multi-Timeframe Technical (25% weight) — Primary module
Evaluate weekly direction + daily rhythm + cycle resonance.
- Weekly bullish + daily pullback = Best buy setup
- Weekly bearish + daily bounce = Trap, avoid longs
- Both aligned = Strongest signal (either direction)
- Risk-reward ratio from key support/resistance levels

### Module 5: Event Calendar (15% weight)
Evaluate upcoming catalysts: earnings, FOMC, options expiration, IV vs HV.
- Earnings within 14 days → Position sizing caution, IV premium
- FOMC meeting → Potential volatility event
- IV >> HV → Market pricing in a move, options expensive

### Module 6: Sentiment & Flow (15% weight)
Evaluate news sentiment, analyst ratings/targets, institutional positioning.
- Analyst upgrades + rising price targets → Positive consensus shift
- Institutional accumulation → Smart money bullish
- Extreme retail optimism (>85% bulls) → Contrarian warning

## Scoring Guidelines

### Strong Buy (80-100):
- Weekly and daily both bullish (strong resonance)
- Macro supportive (offensive mode)
- Fundamentals solid (reasonable valuation + growth)
- No major risk events imminent
- Positive sentiment with institutional backing

### Buy (60-79):
- Weekly bullish, daily pulling back to support
- Macro at least neutral
- Fundamentals acceptable
- One minor concern allowed

### Hold/Watch (40-59):
- Mixed signals across timeframes
- Approaching event risk (earnings, FOMC)
- Valuation stretched but momentum intact
- Needs specific trigger to act

### Sell/Avoid (0-39):
- Weekly bearish or breakdown
- Macro risk-off
- Deteriorating fundamentals
- Negative sentiment shift

## Output Format

You MUST output a single JSON object. Do not include any text outside the JSON.
The JSON must contain ALL of the following fields:

```json
{
    "stock_name": "Apple Inc.",
    "sentiment_score": 72,
    "trend_prediction": "Bullish",
    "operation_advice": "Buy on Pullback",
    "decision_type": "buy",
    "confidence_level": "High",

    "dashboard": {
        "core_conclusion": {
            "one_sentence": "Weekly uptrend intact with daily pullback to MA10 support — ideal entry zone.",
            "signal_type": "Buy Signal",
            "position_advice": {
                "no_position": "Enter 50% position at current level, add on daily breakout above resistance.",
                "has_position": "Hold current position. Add if daily confirms with volume."
            }
        },
        "data_perspective": {
            "trend_status": {
                "weekly_trend": "Bullish (MA10>MA20>MA50)",
                "daily_trend": "Consolidating near MA10",
                "cycle_resonance": "Bullish pullback buy opportunity",
                "is_bullish": true
            },
            "price_position": {
                "current_price": 185.50,
                "vs_weekly_ma": "Above all weekly MAs",
                "vs_daily_ma": "Testing MA10 support"
            },
            "volume_analysis": {
                "volume_ratio": 0.75,
                "volume_status": "Below average — healthy consolidation",
                "interpretation": "Low volume pullback in uptrend = bullish"
            }
        },
        "intelligence": {
            "latest_news": "Key news summary here",
            "risk_alerts": ["Risk item 1", "Risk item 2"],
            "positive_catalysts": ["Catalyst 1", "Catalyst 2"],
            "sentiment_summary": "Overall market sentiment assessment"
        },
        "battle_plan": {
            "scenarios": [
                {
                    "name": "Breakout",
                    "trigger": "Daily close above $190 with above-average volume",
                    "entry": 190.50,
                    "stop_loss": 184.00,
                    "target": 205.00,
                    "position_pct": 8,
                    "risk_reward": "2.2:1"
                },
                {
                    "name": "Pullback",
                    "trigger": "Bounce from MA20 at $182 with RSI oversold",
                    "entry": 183.00,
                    "stop_loss": 178.00,
                    "target": 198.00,
                    "position_pct": 10,
                    "risk_reward": "3.0:1"
                },
                {
                    "name": "Breakdown",
                    "trigger": "Close below $178 on heavy volume",
                    "action": "Do not participate. Wait for stabilization."
                }
            ],
            "sniper_points": {
                "ideal_buy": "$183.00 (MA20 support)",
                "secondary_buy": "$190.50 (breakout confirmation)",
                "stop_loss": "$178.00 (below MA50)",
                "take_profit": "$205.00 (prior high)"
            },
            "action_checklist": [
                "Weekly MA alignment: MA10>MA20>MA50",
                "Daily RSI not overbought (55.3)",
                "Volume declining on pullback (healthy)",
                "No earnings within 14 days",
                "Sector (XLK) outperforming SPY"
            ],
            "risk_warnings": [
                "FOMC meeting on 02/20 may increase volatility",
                "IV elevated vs HV — options expensive",
                "If SPY breaks below MA50, exit all longs"
            ]
        },
        "us_modules": {
            "macro": {"score": 72, "signal": "Offensive mode — market supportive", "weight": 15},
            "sector": {"score": 78, "signal": "Sector outperforming SPY", "weight": 15},
            "fundamental": {"score": 65, "signal": "Fair valuation, solid growth", "weight": 15},
            "technical": {"score": 62, "signal": "Weekly bullish, daily consolidating", "weight": 25},
            "events": {"score": 55, "signal": "FOMC approaching, monitor", "weight": 15},
            "sentiment": {"score": 70, "signal": "Analyst consensus positive", "weight": 15},
            "weighted_total": 66.5
        }
    },

    "analysis_summary": "Concise 2-3 sentence overall assessment.",
    "key_points": "Point 1, Point 2, Point 3",
    "risk_warning": "Primary risk factors to watch",
    "trend_analysis": "Multi-timeframe trend assessment",
    "technical_analysis": "Technical indicators synthesis",
    "ma_analysis": "Moving average system analysis",
    "volume_analysis": "Volume pattern analysis",
    "fundamental_analysis": "Fundamental health summary",
    "sector_position": "Sector positioning and relative strength",
    "news_summary": "Recent news impact summary",
    "market_sentiment": "Overall sentiment assessment",
    "search_performed": true,
    "data_sources": "Technical data + Fundamental data + News intelligence"
}
```

## Critical Rules
1. All prices in USD. Use the EXACT ticker and name provided.
2. Sniper points must be specific prices, not ranges.
3. At least 2 scenarios in battle_plan (bullish + bearish case).
4. Risk warnings must be specific and actionable (not generic).
5. The us_modules weighted_total must be mathematically correct.
6. Output ONLY the JSON object — no markdown, no commentary.
"""


def build_us_stock_prompt(context: Dict[str, Any], news_context: Optional[str] = None) -> str:
    """
    Build the US stock analysis user prompt with all available module data.

    Args:
        context: Enhanced analysis context containing 'us_stock_bundle' and standard fields
        news_context: Pre-formatted news text from SearchService

    Returns:
        Formatted prompt string
    """
    code = context.get("code", "UNKNOWN")
    stock_name = context.get("stock_name", code)
    date = context.get("date", "unknown")
    bundle = context.get("us_stock_bundle", {})

    sections = []

    # Header
    sections.append(f"# Decision Dashboard Analysis Request\n")
    sections.append(f"**Stock**: {stock_name} ({code})")
    sections.append(f"**Date**: {date}\n")

    # Section 1: Basic price data
    sections.append(_build_price_section(context))

    # Section 2: Multi-Timeframe Technical (P0)
    technical = bundle.get("technical")
    if technical:
        sections.append(_build_technical_section(technical))

    # Section 3: Macro Environment (P1)
    macro = bundle.get("macro")
    if macro:
        sections.append(_build_macro_section(macro))

    # Section 4: Fundamental Snapshot (P1)
    fundamental = bundle.get("fundamental")
    if fundamental:
        sections.append(_build_fundamental_section(fundamental))

    # Section 5: Sector Context (P2)
    sector = bundle.get("sector")
    if sector:
        sections.append(_build_sector_section(sector))

    # Section 6: Event Calendar (P2)
    events = bundle.get("events")
    if events:
        sections.append(_build_events_section(events))

    # Section 7: Sentiment & Flow (P3)
    sentiment = bundle.get("sentiment")
    if sentiment:
        sections.append(_build_sentiment_section(sentiment))

    # Section 8: News Intelligence
    if news_context:
        sections.append("---\n## News Intelligence\n")
        sections.append(news_context)

    # Section 9: Analysis Task
    sections.append(_build_task_section(code, stock_name, bundle))

    return "\n\n".join(sections)


def _build_price_section(context: Dict[str, Any]) -> str:
    """Build basic price data section."""
    today = context.get("today", {}) or {}
    realtime = context.get("realtime", {}) or {}
    yesterday = context.get("yesterday", {}) or {}

    lines = ["---\n## Current Market Data\n"]
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")

    price = realtime.get("price") or today.get("close")
    lines.append(f"| Current Price | ${_fmt(price)} |")
    lines.append(f"| Open | ${_fmt(today.get('open'))} |")
    lines.append(f"| High | ${_fmt(today.get('high'))} |")
    lines.append(f"| Low | ${_fmt(today.get('low'))} |")
    lines.append(f"| Previous Close | ${_fmt(yesterday.get('close'))} |")

    pct_chg = today.get("pct_chg")
    if pct_chg is not None:
        lines.append(f"| Change % | {_fmt_pct(pct_chg)} |")

    vol = today.get("volume")
    if vol is not None:
        lines.append(f"| Volume | {_fmt_vol(vol)} |")

    amount = today.get("amount")
    if amount is not None:
        lines.append(f"| Turnover | ${_fmt_amount(amount)} |")

    # Realtime extras
    vr = realtime.get("volume_ratio")
    if vr is not None:
        lines.append(f"| Volume Ratio | {_fmt(vr)} |")
    tr = realtime.get("turnover_rate")
    if tr is not None:
        lines.append(f"| Turnover Rate | {_fmt_pct(tr)} |")
    pe = realtime.get("pe_ratio")
    if pe is not None:
        lines.append(f"| PE (dynamic) | {_fmt(pe)} |")

    return "\n".join(lines)


def _build_technical_section(tech: Dict[str, Any]) -> str:
    """Build multi-timeframe technical analysis section."""
    lines = ["---\n## Module 4: Multi-Timeframe Technical Analysis (25% weight)\n"]

    # Weekly
    weekly = tech.get("weekly", {})
    lines.append("### Weekly Timeframe (Direction)")
    lines.append("| Indicator | Value |")
    lines.append("|-----------|-------|")
    lines.append(f"| Trend | {weekly.get('trend', 'N/A')} |")
    lines.append(f"| MA Alignment | {weekly.get('ma_alignment', 'N/A')} |")
    lines.append(f"| MACD Status | {weekly.get('macd_status', 'N/A')} |")
    lines.append(f"| MACD Bar Trend | {weekly.get('macd_bar_trend', 'N/A')} |")
    lines.append(f"| Price vs MAs | {weekly.get('price_vs_ma', 'N/A')} |")

    # Daily
    daily = tech.get("daily", {})
    lines.append("\n### Daily Timeframe (Rhythm)")
    lines.append("| Indicator | Value |")
    lines.append("|-----------|-------|")
    lines.append(f"| Trend | {daily.get('trend', 'N/A')} |")
    lines.append(f"| MA Alignment | {daily.get('ma_alignment', 'N/A')} |")
    lines.append(f"| RSI(14) | {daily.get('rsi', 'N/A')} ({daily.get('rsi_signal', '')}) |")
    lines.append(f"| Bollinger Position | {daily.get('bollinger_position', 'N/A')} |")
    lines.append(f"| Bollinger Bandwidth | {daily.get('bollinger_bandwidth', 'N/A')}% |")
    lines.append(f"| MACD Status | {daily.get('macd_status', 'N/A')} |")
    lines.append(f"| Volume Ratio (5d) | {daily.get('volume_ratio', 'N/A')} |")
    lines.append(f"| Volume Signal | {daily.get('volume_signal', 'N/A')} |")

    # Resonance
    lines.append(f"\n### Cycle Resonance")
    lines.append(f"**{tech.get('cycle_resonance', 'N/A')}**: {tech.get('resonance_description', '')}")

    # Key levels
    levels = tech.get("key_levels", {})
    if levels:
        lines.append("\n### Key Price Levels")
        lines.append("| Level | Price |")
        lines.append("|-------|-------|")
        for key in ["resistance_2", "resistance_1", "current", "support_1", "support_2"]:
            if key in levels:
                name = levels.get(f"{key}_name", key.replace("_", " ").title())
                lines.append(f"| {name} | ${_fmt(levels[key])} |")
        rr = tech.get("risk_reward_ratio", 0)
        if rr > 0:
            lines.append(f"\n**Risk/Reward Ratio**: {rr:.1f} : 1")

    lines.append(f"\n**Technical Score**: {tech.get('score', 'N/A')}/100")

    return "\n".join(lines)


def _build_macro_section(macro: Dict[str, Any]) -> str:
    """Build macro environment section."""
    lines = ["---\n## Module 1: Macro Environment (15% weight)\n"]
    lines.append("| Indicator | Value | Signal |")
    lines.append("|-----------|-------|--------|")

    details = macro.get("details", {})
    lines.append(f"| SPY vs MA50 | {_fmt_pct(macro.get('spy_vs_ma50_pct'))} | {macro.get('spy_trend', '')} |")
    lines.append(f"| VIX | {_fmt(macro.get('vix'))} | {macro.get('vix_signal', '')} |")
    lines.append(f"| 10Y Yield | {_fmt_pct(macro.get('us10y_yield'))} | |")
    lines.append(f"| Dollar (DXY) | {_fmt(macro.get('dxy'))} | |")

    lines.append(f"\n**Market Regime**: {macro.get('market_regime', 'N/A')}")
    lines.append(f"**Macro Score**: {macro.get('score', 'N/A')}/100")

    return "\n".join(lines)


def _build_fundamental_section(fund: Dict[str, Any]) -> str:
    """Build fundamental snapshot section."""
    lines = ["---\n## Module 3: Fundamental Snapshot (15% weight)\n"]

    lines.append("### Valuation")
    lines.append("| Metric | Value | Signal |")
    lines.append("|--------|-------|--------|")
    lines.append(f"| PE (TTM) | {_fmt(fund.get('pe_ttm'))} | {fund.get('valuation_signal', '')} |")
    lines.append(f"| PE (Forward) | {_fmt(fund.get('pe_forward'))} | |")
    lines.append(f"| PEG | {_fmt(fund.get('peg'))} | |")
    lines.append(f"| P/S (TTM) | {_fmt(fund.get('ps_ttm'))} | |")

    lines.append("\n### Growth")
    lines.append("| Metric | Value | Signal |")
    lines.append("|--------|-------|--------|")
    lines.append(f"| Revenue Growth (YoY) | {_fmt_pct(fund.get('revenue_growth_yoy'))} | {fund.get('growth_signal', '')} |")
    lines.append(f"| Earnings Growth (YoY) | {_fmt_pct(fund.get('earnings_growth_yoy'))} | |")

    lines.append("\n### Financial Health")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Gross Margin | {_fmt_pct(fund.get('gross_margin'))} |")
    lines.append(f"| Free Cash Flow | ${_fmt_amount(fund.get('free_cashflow'))} |")
    lines.append(f"| Debt/Equity | {_fmt(fund.get('debt_to_equity'))} |")
    lines.append(f"| Institutional Ownership | {_fmt_pct(fund.get('institutional_pct'))} |")

    lines.append(f"\n**Fundamental Score**: {fund.get('score', 'N/A')}/100")

    return "\n".join(lines)


def _build_sector_section(sector: Dict[str, Any]) -> str:
    """Build sector context section."""
    lines = ["---\n## Module 2: Sector Context (15% weight)\n"]
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Sector ETF | {sector.get('etf', 'N/A')} ({sector.get('sector_name', '')}) |")
    lines.append(f"| ETF 5d Return | {_fmt_pct(sector.get('etf_5d_return'))} |")
    lines.append(f"| SPY 5d Return | {_fmt_pct(sector.get('spy_5d_return'))} |")
    lines.append(f"| Relative Strength | {sector.get('relative_strength', 'N/A')} |")
    lines.append(f"| Stock Rank in Sector | {sector.get('stock_rank', 'N/A')} |")
    lines.append(f"| Stock 5d Return | {_fmt_pct(sector.get('stock_5d_return'))} |")
    lines.append(f"\n**Sector Score**: {sector.get('score', 'N/A')}/100")
    return "\n".join(lines)


def _build_events_section(events: Dict[str, Any]) -> str:
    """Build event calendar section."""
    lines = ["---\n## Module 5: Event Calendar & Catalysts (15% weight)\n"]

    lines.append("### Upcoming Events (Next 30 Days)")
    event_list = events.get("upcoming_events", [])
    if event_list:
        for evt in event_list:
            lines.append(f"- **{evt.get('date', '?')}** — {evt.get('event', '?')}: {evt.get('impact', '')}")
    else:
        lines.append("- No major events in the next 30 days")

    lines.append("\n### Volatility")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Implied Volatility (IV) | {_fmt_pct(events.get('iv'))} |")
    lines.append(f"| Historical Volatility (HV) | {_fmt_pct(events.get('hv'))} |")
    iv = events.get("iv")
    hv = events.get("hv")
    if iv is not None and hv is not None and hv > 0:
        iv_hv = "IV > HV (options expensive)" if iv > hv else "IV < HV (options cheap)"
        lines.append(f"| IV vs HV | {iv_hv} |")

    lines.append(f"\n**Events Score**: {events.get('score', 'N/A')}/100")
    return "\n".join(lines)


def _build_sentiment_section(sentiment: Dict[str, Any]) -> str:
    """Build sentiment & flow section."""
    lines = ["---\n## Module 6: Sentiment & Flow (15% weight)\n"]

    lines.append("### Analyst Consensus")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Consensus Rating | {sentiment.get('analyst_consensus', 'N/A')} |")
    lines.append(f"| Buy / Hold / Sell | {sentiment.get('analyst_buy', '?')} / {sentiment.get('analyst_hold', '?')} / {sentiment.get('analyst_sell', '?')} |")
    lines.append(f"| Target Price (Mean) | ${_fmt(sentiment.get('target_mean'))} |")
    lines.append(f"| Target Price (High) | ${_fmt(sentiment.get('target_high'))} |")
    lines.append(f"| Target Price (Low) | ${_fmt(sentiment.get('target_low'))} |")
    lines.append(f"| Target Upside | {_fmt_pct(sentiment.get('target_upside_pct'))} |")
    lines.append(f"| # of Analysts | {sentiment.get('num_analysts', 'N/A')} |")

    inst = sentiment.get("institutional_pct")
    if inst is not None:
        lines.append(f"\n### Institutional Ownership")
        lines.append(f"- Institutional holding: {_fmt_pct(inst)}")

    top_holders = sentiment.get("top_holders", [])
    if top_holders:
        holder_names = []
        for h in top_holders[:5]:
            if isinstance(h, dict):
                name = h.get("name", "Unknown")
                pct = h.get("pct")
                holder_names.append(f"{name} ({_fmt_pct(pct)})" if pct is not None else name)
            else:
                holder_names.append(str(h))
        lines.append("- Top holders: " + ", ".join(holder_names))

    news_sentiment = sentiment.get("news_sentiment")
    if news_sentiment:
        pos = sentiment.get("news_positive_count", 0)
        neg = sentiment.get("news_negative_count", 0)
        lines.append(f"\n### News Sentiment")
        lines.append(f"- Overall: {news_sentiment} (positive keywords: {pos}, negative: {neg})")

    lines.append(f"\n**Sentiment Score**: {sentiment.get('score', 'N/A')}/100")
    return "\n".join(lines)


def _build_task_section(code: str, stock_name: str, bundle: Dict[str, Any]) -> str:
    """Build the analysis task instructions."""
    available = [m for m in ["technical", "macro", "sector", "fundamental", "events", "sentiment"] if bundle.get(m)]
    missing = [m for m in ["technical", "macro", "sector", "fundamental", "events", "sentiment"] if not bundle.get(m)]

    lines = ["---\n## Analysis Task\n"]
    lines.append(f"Generate a **Decision Dashboard** for **{stock_name} ({code})**.\n")
    lines.append(f"**Available modules**: {', '.join(available) if available else 'None'}")
    if missing:
        lines.append(f"**Unavailable modules**: {', '.join(missing)} — assign neutral scores (50) for these.\n")

    lines.append("### Requirements:")
    lines.append("1. Score each of the 6 modules (0-100) and compute weighted total")
    lines.append("2. Provide at least 2 trade scenarios (bullish + bearish case) with specific prices")
    lines.append("3. List top 3 risk warnings that are specific to this stock/situation")
    lines.append("4. The `action_checklist` should list 5+ items with clear pass/fail status")
    lines.append("5. Output ONLY valid JSON — no markdown fences, no explanatory text")

    return "\n".join(lines)


# ── Formatting Helpers ──────────────────────────────────────────────────

def _fmt(value) -> str:
    """Format a numeric value or return N/A."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"{v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"{v / 1e6:.2f}M"
        return f"{v:.2f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value) -> str:
    """Format a percentage value."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return str(value)


def _fmt_vol(value) -> str:
    """Format volume."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if v >= 1e9:
            return f"{v / 1e9:.2f}B"
        if v >= 1e6:
            return f"{v / 1e6:.2f}M"
        if v >= 1e3:
            return f"{v / 1e3:.1f}K"
        return f"{v:.0f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_amount(value) -> str:
    """Format monetary amount."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if abs(v) >= 1e12:
            return f"{v / 1e12:.2f}T"
        if abs(v) >= 1e9:
            return f"{v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"{v / 1e6:.2f}M"
        if abs(v) >= 1e3:
            return f"{v / 1e3:.1f}K"
        return f"{v:.2f}"
    except (TypeError, ValueError):
        return str(value)
