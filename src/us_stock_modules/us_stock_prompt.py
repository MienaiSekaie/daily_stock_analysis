# -*- coding: utf-8 -*-
"""
US Stock Analysis Prompt Templates

English-language system prompt and user prompt builder for US stock
multi-dimensional analysis. Produces JSON output compatible with
the existing AnalysisResult/dashboard structure.
"""

from typing import Any, Dict, Optional


# ── Module-Level System Prompts ───────────────────────────────────────────

MODULE_SYSTEM_PROMPTS = {
    "macro": """You are a senior US macro strategist. Analyze the macro environment data provided and deliver a \
focused assessment of how the current market regime affects equity positioning for the given stock.

Your analysis should address:
1. Overall market health: Is SPY trending above or below its MA50? What does this mean for broad equity exposure?
2. Volatility regime: Is VIX signaling complacency, caution, or panic? How should this affect position sizing?
3. Rate environment: What do Treasury yields imply for equity valuations and growth stocks vs value stocks?
4. Dollar impact: How does USD strength/weakness affect this stock's earnings and competitive position?
5. Regime synthesis: Classify the current environment as offensive (risk-on), defensive (selective), or risk-off.

Provide concrete, actionable conclusions — not generic commentary.

IMPORTANT: All text content in the JSON (analysis, key_findings, risk_factors, signal) MUST be written in Chinese (中文). Only keep stock tickers, technical indicator names (e.g. VIX, RSI, MA50), and price numbers in English.

Output a JSON object with these fields:
{
    "analysis": "2-3段分析，覆盖上述要点并引用具体数据",
    "key_findings": ["3-5条具体发现，如'VIX处于18.5低位，支持积极建仓'"],
    "risk_factors": ["1-3条宏观风险，如'10Y国债收益率达4.8%，可能压制成长股估值'"],
    "signal": "一句话信号总结，如'进攻型市场环境——有利于做多'",
    "outlook": "MUST be exactly one of: bullish, neutral, or bearish — choose based on your analysis, do NOT default to neutral"
}

CRITICAL — Outlook Rules:
- The "outlook" MUST be consistent with the module data score provided in the user prompt.
- Score >= 65 → outlook should be "bullish"
- Score <= 35 → outlook should be "bearish"
- Score 36-64 → outlook should be "neutral" ONLY if signals are genuinely mixed; otherwise lean bullish/bearish based on your qualitative analysis.
- NEVER default to "neutral" — actively decide based on the data.

Output ONLY the JSON object — no markdown fences, no commentary.""",

    "sector": """You are a sector rotation analyst specializing in relative strength analysis. Analyze the sector \
context data provided and assess whether the sector dynamics provide tailwind or headwind for the given stock.

Your analysis should address:
1. Sector vs Market: Is the sector ETF outperforming or underperforming SPY over the 5-day window? What's the trend?
2. Stock vs Sector: Where does this stock rank within its sector peers? Is it a leader or laggard?
3. Sector momentum: Is money rotating into or out of this sector? What does peer performance indicate?
4. Relative strength implications: What does the stock's relative positioning tell us about institutional interest?
5. Actionable conclusion: Should sector dynamics encourage or discourage new positions in this stock?

IMPORTANT: All text content in the JSON (analysis, key_findings, risk_factors, signal) MUST be written in Chinese (中文). Only keep stock tickers, ETF names (e.g. XLK, SPY), and price/percentage numbers in English.

Output a JSON object with these fields:
{
    "analysis": "2-3段板块动态分析，引用具体数据",
    "key_findings": ["3-5条具体发现，如'XLK +3.2% vs SPY +1.1%——板块强劲顺风'"],
    "risk_factors": ["1-3条板块风险，如'个股在板块内排名12/15——尽管板块走强但个股落后'"],
    "signal": "一句话信号总结",
    "outlook": "MUST be exactly one of: bullish, neutral, or bearish — choose based on your analysis, do NOT default to neutral"
}

CRITICAL — Outlook Rules:
- The "outlook" MUST be consistent with the module data score provided in the user prompt.
- Score >= 65 → outlook should be "bullish"
- Score <= 35 → outlook should be "bearish"
- Score 36-64 → outlook should be "neutral" ONLY if signals are genuinely mixed; otherwise lean bullish/bearish based on your qualitative analysis.
- NEVER default to "neutral" — actively decide based on the data.

Output ONLY the JSON object — no markdown fences, no commentary.""",

    "fundamental": """You are a fundamental equity research analyst. Analyze the valuation, growth, profitability, \
and financial health metrics provided and determine whether the stock is attractively priced relative to its \
growth trajectory.

Your analysis should address:
1. Valuation assessment: Is the PE/PEG/PS ratio justified by the company's growth rate? Compare to typical ranges.
2. Growth trajectory: Are revenue and earnings growth accelerating, stable, or decelerating?
3. Profitability quality: Are gross/operating/net margins expanding or contracting? What does this signal?
4. Balance sheet health: Evaluate debt-to-equity ratio, free cash flow, and current ratio. Any financial stress?
5. Institutional validation: What does institutional ownership level suggest about smart money confidence?
6. Synthesis: Is this a growth-at-reasonable-price (GARP), overvalued momentum, value trap, or quality compounder?

IMPORTANT: All text content in the JSON (analysis, key_findings, risk_factors, signal) MUST be written in Chinese (中文). Only keep financial metric names (e.g. PE, PEG, FCF), stock tickers, and numbers in English.

Output a JSON object with these fields:
{
    "analysis": "2-3段基本面分析，引用具体财务指标",
    "key_findings": ["3-5条具体发现，如'PEG仅0.8且盈利增速35%——价格极具吸引力的成长股'"],
    "risk_factors": ["1-3条基本面风险，如'Debt/Equity高达180%——高杠杆资产负债表在加息环境下脆弱'"],
    "signal": "一句话信号总结",
    "outlook": "MUST be exactly one of: bullish, neutral, or bearish — choose based on your analysis, do NOT default to neutral"
}

CRITICAL — Outlook Rules:
- The "outlook" MUST be consistent with the module data score provided in the user prompt.
- Score >= 65 → outlook should be "bullish"
- Score <= 35 → outlook should be "bearish"
- Score 36-64 → outlook should be "neutral" ONLY if signals are genuinely mixed; otherwise lean bullish/bearish based on your qualitative analysis.
- NEVER default to "neutral" — actively decide based on the data.

Output ONLY the JSON object — no markdown fences, no commentary.""",

    "technical": """You are a multi-timeframe technical analyst specializing in trend trading with a \
"weekly direction + daily rhythm" approach. Analyze the technical data provided and determine the optimal \
entry/exit strategy.

Your analysis should address:
1. Weekly trend: Is the weekly trend bullish, bearish, or consolidating? What does MA alignment tell us?
2. Daily rhythm: Where is price in the daily cycle? Is it extended, at support, or in no-man's-land?
3. Cycle resonance: Do weekly and daily timeframes agree or conflict? What does the resonance signal mean?
4. Momentum indicators: What do RSI, MACD, and Bollinger Bands confirm or warn about?
5. Volume confirmation: Is volume supporting the price move? Any divergences?
6. Key levels strategy: Identify the most important support/resistance levels and the risk/reward ratio.
7. Optimal setup: What is the ideal entry trigger, stop loss, and target based on the technical picture?
8. Yesterday's price action: If the stock had a significant daily move (>3%), analyze whether it broke key \
support/resistance, triggered stop levels, or changed the technical setup. Assess whether the move signals \
a reversal, continuation, or is likely a temporary overreaction that may revert.

IMPORTANT: All text content in the JSON (analysis, key_findings, risk_factors, signal) MUST be written in Chinese (中文). Only keep technical indicator names (e.g. RSI, MACD, MA10, Bollinger), stock tickers, and price numbers in English.

Output a JSON object with these fields:
{
    "analysis": "2-3段技术分析，覆盖周线/日线共振、动量和关键点位",
    "key_findings": ["3-5条具体发现，如'周线看多且日线回踩MA10——教科书级买入机会'"],
    "risk_factors": ["1-3条技术风险，如'RSI达72超买区——进一步上涨前可能先回调'"],
    "signal": "一句话信号总结",
    "outlook": "MUST be exactly one of: bullish, neutral, or bearish — choose based on your analysis, do NOT default to neutral"
}

CRITICAL — Outlook Rules:
- The "outlook" MUST be consistent with the module data score provided in the user prompt.
- Score >= 65 → outlook should be "bullish"
- Score <= 35 → outlook should be "bearish"
- Score 36-64 → outlook should be "neutral" ONLY if signals are genuinely mixed; otherwise lean bullish/bearish based on your qualitative analysis.
- NEVER default to "neutral" — actively decide based on the data.

Output ONLY the JSON object — no markdown fences, no commentary.""",

    "events": """You are an event-driven trading strategist specializing in catalyst analysis and volatility \
assessment. Analyze the event calendar and volatility data provided and assess timing risk for positioning.

Your analysis should address:
1. Earnings proximity: How close is the next earnings report? Should traders position before or after?
2. FOMC impact: Is a Fed decision imminent? How might rate expectations affect this stock specifically?
3. Options expiration: Could OPEX-related hedging flows affect near-term price action?
4. Volatility assessment: Compare implied vs historical volatility. Are options cheap or expensive?
5. Event overlap: Are multiple events converging? What is the compounded risk of overlapping catalysts?
6. Position sizing: How should upcoming events affect position size and entry timing?

IMPORTANT: All text content in the JSON (analysis, key_findings, risk_factors, signal) MUST be written in Chinese (中文). Only keep event names (e.g. FOMC, OPEX, Earnings), stock tickers, dates, and numbers in English.

Output a JSON object with these fields:
{
    "analysis": "2-3段关于事件驱动的持仓风险与机会分析",
    "key_findings": ["3-5条具体发现，如'距财报仅8天——IV溢价可能扩大，避免卖出看跌期权'"],
    "risk_factors": ["1-3条事件风险，如'FOMC与财报在同一周——极端二元风险'"],
    "signal": "一句话信号总结",
    "outlook": "MUST be exactly one of: bullish, neutral, or bearish — choose based on your analysis, do NOT default to neutral"
}

CRITICAL — Outlook Rules:
- The "outlook" MUST be consistent with the module data score provided in the user prompt.
- Score >= 65 → outlook should be "bullish"
- Score <= 35 → outlook should be "bearish"
- Score 36-64 → outlook should be "neutral" ONLY if signals are genuinely mixed; otherwise lean bullish/bearish based on your qualitative analysis.
- NEVER default to "neutral" — actively decide based on the data.

Output ONLY the JSON object — no markdown fences, no commentary.""",

    "sentiment": """You are a sentiment and institutional flow analyst. Analyze the analyst ratings, price targets, \
institutional positioning, and news sentiment data provided. Identify consensus shifts and contrarian signals.

Your analysis should address:
1. Analyst consensus: What is the overall rating distribution? Are analysts converging or diverging?
2. Price target gap: How much upside/downside do analysts see? Is the mean target realistic given technicals?
3. Institutional positioning: What does institutional ownership level signal? Are big players accumulating?
4. News sentiment: What is the prevailing news tone? Any significant positive or negative catalysts in coverage?
5. Contrarian check: Are there signs of excessive bullishness or bearishness that could reverse?
6. Sentiment synthesis: Is the consensus supportive of the current price, or is there a disconnect?

IMPORTANT: All text content in the JSON (analysis, key_findings, risk_factors, signal) MUST be written in Chinese (中文). Only keep stock tickers, analyst rating terms (e.g. Buy/Hold/Sell), and numbers in English.

Output a JSON object with these fields:
{
    "analysis": "2-3段情绪与资金流向分析，引用具体数据",
    "key_findings": ["3-5条具体发现，如'分析师共识：28 Buy / 5 Hold / 1 Sell——强烈看多倾向'"],
    "risk_factors": ["1-3条情绪风险，如'目标均价仅高出当前价5%——上行空间共识有限'"],
    "signal": "一句话信号总结",
    "outlook": "MUST be exactly one of: bullish, neutral, or bearish — choose based on your analysis, do NOT default to neutral"
}

CRITICAL — Outlook Rules:
- The "outlook" MUST be consistent with the module data score provided in the user prompt.
- Score >= 65 → outlook should be "bullish"
- Score <= 35 → outlook should be "bearish"
- Score 36-64 → outlook should be "neutral" ONLY if signals are genuinely mixed; otherwise lean bullish/bearish based on your qualitative analysis.
- NEVER default to "neutral" — actively decide based on the data.

Output ONLY the JSON object — no markdown fences, no commentary.""",
}


def build_module_prompt(module_name: str, module_data: Dict[str, Any], code: str, stock_name: str) -> str:
    """
    Build a focused user prompt for a single module LLM call.

    Reuses the existing _build_*_section() functions for consistent data formatting,
    but only includes the single relevant module's data.

    Args:
        module_name: One of 'macro', 'sector', 'fundamental', 'technical', 'events', 'sentiment'
        module_data: Serialized module result dict
        code: Stock ticker
        stock_name: Stock name

    Returns:
        Formatted prompt string
    """
    section_builders = {
        "macro": _build_macro_section,
        "sector": _build_sector_section,
        "fundamental": _build_fundamental_section,
        "technical": _build_technical_section,
        "events": _build_events_section,
        "sentiment": _build_sentiment_section,
    }

    lines = [
        f"# {module_name.title()} Analysis for {stock_name} ({code})\n",
        f"Analyze the following {module_name} data for **{stock_name} ({code})**.",
        f"Module data score: {module_data.get('score', 'N/A')}/100\n",
    ]

    builder = section_builders.get(module_name)
    if builder:
        lines.append(builder(module_data))

    return "\n".join(lines)


# ── Synthesis System Prompt (Final 7th Call) ──────────────────────────────

US_STOCK_SYSTEM_PROMPT = """You are a senior US equity trading strategist. You are given 6 expert module analyses \
from domain specialists (macro, sector, fundamental, technical, events, sentiment). Your job is to SYNTHESIZE \
these analyses into a unified Decision Dashboard with actionable trade recommendations.

## IMPORTANT: Output Language
ALL analysis text, summaries, advice, and commentary MUST be written in **Chinese (中文)**.
Only keep stock names, tickers, technical terms (MA, RSI, MACD, VIX, etc.), and specific price numbers in English.

## Your Role
- You are the FINAL synthesizer. Each module has already been analyzed by a domain expert.
- Reference specific findings from the module analyses in your KEY INSIGHTS — do not write generic conclusions.
- Resolve contradictions between modules (e.g., bullish technicals vs bearish fundamentals).
- The us_modules scores and signals should reflect the expert analyses provided.
- Focus on the INTERPLAY between modules — how do they reinforce or contradict each other?
- If the stock had a significant daily move (>3%), explicitly address whether it was driven by broad market \
conditions (check macro module SPY 1d Change data) or stock-specific factors. This context MUST appear in \
the analysis_summary and influence the battle_plan scenarios.

## Module Weights
- Technical (25%): Multi-timeframe trend alignment — PRIMARY signal
- Macro (15%): Market regime and risk environment
- Sector (15%): Sector relative strength and rotation
- Fundamental (15%): Valuation, growth, financial health
- Events (15%): Catalyst timing and volatility risk
- Sentiment (15%): Consensus, institutional flow, news tone

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
            "one_sentence": "周线上升趋势完好，日线回踩MA10支撑——理想的加仓区间",
            "signal_type": "买入信号",
            "position_advice": {
                "no_position": "在当前价位建仓50%，日线放量突破阻力位后加仓",
                "has_position": "继续持有。若日线放量确认突破可加仓"
            }
        },
        "data_perspective": {
            "trend_status": {
                "weekly_trend": "看多 (MA10>MA20>MA50 多头排列)",
                "daily_trend": "MA10附近整理",
                "cycle_resonance": "周线看多+日线回踩=买入机会",
                "is_bullish": true
            },
            "price_position": {
                "current_price": 185.50,
                "vs_weekly_ma": "位于所有周线均线之上",
                "vs_daily_ma": "测试MA10支撑"
            },
            "volume_analysis": {
                "volume_ratio": 0.75,
                "volume_status": "低于均值——健康整理缩量",
                "interpretation": "上升趋势中缩量回踩=看多信号"
            }
        },
        "intelligence": {
            "latest_news": "关键新闻摘要",
            "risk_alerts": ["风险因素1", "风险因素2"],
            "positive_catalysts": ["利好催化剂1", "利好催化剂2"],
            "sentiment_summary": "市场情绪综合评估"
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

    "analysis_summary": "这是 KEY INSIGHTS 区域，必须写成结构化的深度分析（至少300字），包含以下内容：\n1. 【核心判断】一句话总结当前多空态势及主要矛盾\n2. 【多维共振】技术面、基本面、宏观面是否共振？哪些模块互相印证，哪些互相矛盾？\n3. 【关键驱动】当前最重要的2-3个驱动因素（引用模块分析中的具体数据）\n4. 【风险焦点】最需警惕的1-2个风险点（引用模块风险因子中的具体发现）\n5. 【操作节奏】当前是进攻、防守还是观望？明确给出仓位建议和触发条件",
    "key_points": "3-5个核心看点，每个都引用具体模块分析数据",
    "risk_warning": "综合各模块风险因子的核心风险提示",
    "trend_analysis": "综合技术模块的多周期趋势分析",
    "technical_analysis": "技术指标综合研判",
    "ma_analysis": "均线系统分析",
    "volume_analysis": "量能形态分析",
    "fundamental_analysis": "基本面健康度总结",
    "sector_position": "板块定位与相对强度",
    "news_summary": "近期新闻影响摘要",
    "market_sentiment": "市场情绪综合评估",
    "search_performed": true,
    "data_sources": "技术数据 + 基本面数据 + 新闻情报"
}
```

## Critical Rules
1. All analysis text MUST be in Chinese (中文). Prices, tickers, and technical terms can remain in English.
2. The `analysis_summary` (KEY INSIGHTS) MUST be a structured, detailed analysis (at least 300 characters). It must reference specific data from the module analyses — NOT be a vague 2-sentence summary.
3. All prices in USD. Use the EXACT ticker and name provided.
4. The `battle_plan.sniper_points` section is MANDATORY. All 4 fields (ideal_buy, secondary_buy, stop_loss, take_profit) must contain specific USD prices derived from key technical levels — never omit this section.
5. At least 2 scenarios in battle_plan (bullish + bearish case).
6. Risk warnings must be specific and actionable (not generic).
7. The us_modules weighted_total must be mathematically correct.
8. Output ONLY the JSON object — no markdown, no commentary.
"""


def build_us_stock_prompt(
    context: Dict[str, Any],
    news_context: Optional[str] = None,
    module_insights: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build the US stock analysis user prompt.

    When module_insights are provided (7-call mode), the prompt includes expert
    module analyses for the synthesis LLM to integrate. Key raw data metrics
    (price, key levels) are still included for specific price references.

    When module_insights are NOT provided (legacy 1-call mode), the prompt
    includes full raw data tables for the LLM to analyze from scratch.

    Args:
        context: Enhanced analysis context containing 'us_stock_bundle' and standard fields
        news_context: Pre-formatted news text from SearchService
        module_insights: Dict of module LLM analyses (from USStockModuleInsights.to_dict())

    Returns:
        Formatted prompt string
    """
    code = context.get("code", "UNKNOWN")
    stock_name = context.get("stock_name", code)
    date = context.get("date", "unknown")
    bundle = context.get("us_stock_bundle", {})
    has_insights = module_insights is not None and any(v for v in module_insights.values() if v)

    sections = []

    # Header
    sections.append(f"# Decision Dashboard Synthesis Request\n")
    sections.append(f"**Stock**: {stock_name} ({code})")
    sections.append(f"**Date**: {date}\n")

    # Section 1: Basic price data (always include for price reference)
    sections.append(_build_price_section(context))

    if has_insights:
        # 7-call mode: Include expert module analyses + essential raw data
        sections.append(_build_module_insights_section(module_insights))

        # Still include key technical levels for specific price targets
        technical = bundle.get("technical")
        if technical:
            sections.append(_build_technical_key_levels_only(technical))
    else:
        # Legacy 1-call mode: Include full raw data tables
        technical = bundle.get("technical")
        if technical:
            sections.append(_build_technical_section(technical))

        macro = bundle.get("macro")
        if macro:
            sections.append(_build_macro_section(macro))

        fundamental = bundle.get("fundamental")
        if fundamental:
            sections.append(_build_fundamental_section(fundamental))

        sector = bundle.get("sector")
        if sector:
            sections.append(_build_sector_section(sector))

        events = bundle.get("events")
        if events:
            sections.append(_build_events_section(events))

        sentiment = bundle.get("sentiment")
        if sentiment:
            sections.append(_build_sentiment_section(sentiment))

    # News Intelligence
    if news_context:
        sections.append("---\n## News Intelligence\n")
        sections.append(news_context)

    # Analysis Task
    sections.append(_build_synthesis_task_section(code, stock_name, bundle, has_insights))

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

    # Yesterday's performance (for significant move analysis)
    yest_pct = yesterday.get("pct_chg")
    if yest_pct is not None:
        lines.append(f"| Yesterday Change % | {_fmt_pct(yest_pct)} |")
    yest_vol = yesterday.get("volume")
    if yest_vol is not None:
        lines.append(f"| Yesterday Volume | {_fmt_vol(yest_vol)} |")

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
    latest_chg = daily.get("latest_1d_chg_pct")
    if latest_chg is not None:
        lines.append(f"| Latest Day Change % | {_fmt_pct(latest_chg)} |")

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
    lines.append(f"| SPY 1d Change | {_fmt_pct(macro.get('spy_1d_chg_pct'))} | |")
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


def _build_module_insights_section(module_insights: Dict[str, Any]) -> str:
    """Build the expert module analyses section for synthesis mode."""
    display_names = {
        "macro": "Macro Environment",
        "sector": "Sector Context",
        "fundamental": "Fundamental Snapshot",
        "technical": "Multi-Timeframe Technical",
        "events": "Event Calendar & Catalysts",
        "sentiment": "Sentiment & Flow",
    }
    weights = {
        "macro": 15,
        "sector": 15,
        "fundamental": 15,
        "technical": 25,
        "events": 15,
        "sentiment": 15,
    }
    module_order = ["technical", "macro", "fundamental", "sector", "events", "sentiment"]

    lines = ["---\n## Expert Module Analyses\n"]
    lines.append("The following analyses were produced by domain-specialist AI analysts.\n")

    for name in module_order:
        insight = module_insights.get(name)
        if insight is None:
            continue

        display = display_names.get(name, name)
        weight = weights.get(name, 15)
        score = insight.get("score", "N/A")
        outlook = insight.get("outlook", "N/A")

        lines.append(f"### {display} (Weight: {weight}%, Score: {score}/100, Outlook: {outlook})")

        analysis = insight.get("analysis", "")
        if analysis:
            lines.append(f"\n{analysis}")

        findings = insight.get("key_findings", [])
        if findings:
            lines.append("\n**Key Findings:**")
            for f in findings:
                lines.append(f"- {f}")

        risks = insight.get("risk_factors", [])
        if risks:
            lines.append("\n**Risk Factors:**")
            for r in risks:
                lines.append(f"- {r}")

        signal = insight.get("signal", "")
        if signal:
            lines.append(f"\n**Signal:** {signal}")

        lines.append("")  # blank line between modules

    return "\n".join(lines)


def _build_technical_key_levels_only(tech: Dict[str, Any]) -> str:
    """Build a compact key levels section (used in synthesis mode to keep price references)."""
    lines = ["---\n## Key Technical Levels (for price reference)\n"]

    # Key levels
    levels = tech.get("key_levels", {})
    if levels:
        lines.append("| Level | Price |")
        lines.append("|-------|-------|")
        for key in ["resistance_2", "resistance_1", "current", "support_1", "support_2"]:
            if key in levels:
                label = levels.get(f"{key}_name", key.replace("_", " ").title())
                lines.append(f"| {label} | ${_fmt(levels[key])} |")
        rr = tech.get("risk_reward_ratio", 0)
        if rr > 0:
            lines.append(f"\n**Risk/Reward Ratio**: {rr:.1f} : 1")

    # Cycle resonance one-liner
    resonance = tech.get("cycle_resonance")
    if resonance:
        lines.append(f"\n**Cycle Resonance**: {resonance} — {tech.get('resonance_description', '')}")

    return "\n".join(lines)


def _build_synthesis_task_section(
    code: str, stock_name: str, bundle: Dict[str, Any], has_insights: bool
) -> str:
    """Build the analysis task instructions for both synthesis and legacy modes."""
    available = [m for m in ["technical", "macro", "sector", "fundamental", "events", "sentiment"] if bundle.get(m)]
    missing = [m for m in ["technical", "macro", "sector", "fundamental", "events", "sentiment"] if not bundle.get(m)]

    lines = ["---\n## Analysis Task\n"]
    lines.append(f"Generate a **Decision Dashboard** for **{stock_name} ({code})**.\n")
    lines.append(f"**Available modules**: {', '.join(available) if available else 'None'}")
    if missing:
        lines.append(f"**Unavailable modules**: {', '.join(missing)} — assign neutral scores (50) for these.\n")

    lines.append("### Requirements:")

    if has_insights:
        lines.append("1. SYNTHESIZE the 6 expert module analyses above — do not re-analyze raw data")
        lines.append("2. Use the expert-provided scores for each module in `us_modules`, compute weighted total")
        lines.append("3. In `analysis_summary` and `key_points`, reference SPECIFIC findings from the expert analyses")
        lines.append("4. Resolve any contradictions between modules (explain which signal takes priority and why)")
        lines.append("5. Provide at least 2 trade scenarios (bullish + bearish) with SPECIFIC prices from key levels")
        lines.append(
            "6. `battle_plan.sniper_points` is REQUIRED — derive ideal_buy/secondary_buy from support levels, "
            "stop_loss from breakdown level, take_profit from resistance levels"
        )
        lines.append("7. List top 3 risk warnings drawn from the module risk factors")
        lines.append("8. The `action_checklist` should list 5+ items synthesized from all module findings")
        lines.append("9. Output ONLY valid JSON — no markdown fences, no explanatory text")
    else:
        lines.append("1. Score each of the 6 modules (0-100) and compute weighted total")
        lines.append("2. Provide at least 2 trade scenarios (bullish + bearish case) with specific prices")
        lines.append(
            "3. `battle_plan.sniper_points` is REQUIRED — derive specific USD prices from key technical levels"
        )
        lines.append("4. List top 3 risk warnings that are specific to this stock/situation")
        lines.append("5. The `action_checklist` should list 5+ items with clear pass/fail status")
        lines.append("6. Output ONLY valid JSON — no markdown fences, no explanatory text")

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
