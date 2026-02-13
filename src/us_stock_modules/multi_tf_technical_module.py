# -*- coding: utf-8 -*-
"""
Module 4: Multi-Timeframe Technical Analysis

Analyzes weekly and daily timeframes to determine cycle resonance.
- Weekly: defines direction (MA10/MA20/MA50, MACD)
- Daily: defines rhythm (MA5/MA10/MA20, RSI, Bollinger, volume)
- Resonance: combination of weekly + daily trend → actionable signal
- Key levels: support/resistance with risk-reward ratio
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MultiTFResult:
    """Multi-timeframe technical analysis result."""

    # Weekly timeframe
    weekly_trend: str = "unknown"  # "bullish" / "bearish" / "consolidating"
    weekly_ma_alignment: str = ""  # e.g. "MA10>MA20>MA50"
    weekly_macd_status: str = ""  # "golden_cross" / "bullish" / "bearish" / "death_cross"
    weekly_macd_bar_trend: str = ""  # "expanding" / "contracting"
    weekly_price_vs_ma: str = ""  # "above_ma10" / "between_ma10_ma20" / "below_ma50"

    # Daily timeframe
    daily_trend: str = "unknown"
    daily_ma_alignment: str = ""
    daily_rsi: float = 50.0
    daily_rsi_signal: str = "neutral"
    daily_bollinger_position: str = ""  # "above_upper" / "upper_half" / "lower_half" / "below_lower"
    daily_bollinger_bandwidth: float = 0.0  # bandwidth as % of middle band
    daily_macd_status: str = ""
    daily_volume_ratio: float = 1.0
    daily_volume_signal: str = ""  # "heavy_up" / "heavy_down" / "shrink_up" / "shrink_down" / "normal"
    latest_1d_chg_pct: float = 0.0  # Latest day's price change %

    # Cycle resonance
    cycle_resonance: str = ""  # e.g. "bullish_pullback_buy"
    resonance_description: str = ""  # human-readable description

    # Key price levels
    key_levels: Dict[str, float] = field(default_factory=dict)
    risk_reward_ratio: float = 0.0

    # Score
    score: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weekly": {
                "trend": self.weekly_trend,
                "ma_alignment": self.weekly_ma_alignment,
                "macd_status": self.weekly_macd_status,
                "macd_bar_trend": self.weekly_macd_bar_trend,
                "price_vs_ma": self.weekly_price_vs_ma,
            },
            "daily": {
                "trend": self.daily_trend,
                "ma_alignment": self.daily_ma_alignment,
                "rsi": round(self.daily_rsi, 1),
                "rsi_signal": self.daily_rsi_signal,
                "bollinger_position": self.daily_bollinger_position,
                "bollinger_bandwidth": round(self.daily_bollinger_bandwidth, 2),
                "macd_status": self.daily_macd_status,
                "volume_ratio": round(self.daily_volume_ratio, 2),
                "volume_signal": self.daily_volume_signal,
                "latest_1d_chg_pct": round(self.latest_1d_chg_pct, 2),
            },
            "cycle_resonance": self.cycle_resonance,
            "resonance_description": self.resonance_description,
            "key_levels": {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in self.key_levels.items()},
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "score": self.score,
        }


# Cycle resonance matrix: (weekly_trend, daily_trend) → (signal, description)
RESONANCE_MATRIX = {
    ("bullish", "bullish"): (
        "strong_bullish",
        "Weekly bullish + Daily bullish = Strong trend continuation. Consider trend-following entry with tight stop.",
    ),
    ("bullish", "consolidating"): (
        "bullish_pullback_buy",
        "Weekly bullish + Daily consolidating = Pullback buy opportunity. Wait for daily breakout confirmation.",
    ),
    ("bullish", "bearish"): (
        "bullish_correction",
        "Weekly bullish + Daily bearish = Correction within uptrend. Watch for daily trend reversal to go long.",
    ),
    ("consolidating", "bullish"): (
        "range_breakout_attempt",
        "Weekly consolidating + Daily bullish = Potential breakout attempt. Needs weekly confirmation.",
    ),
    ("consolidating", "consolidating"): (
        "range_bound",
        "Weekly and daily both consolidating = Range-bound. Trade the range or wait for directional breakout.",
    ),
    ("consolidating", "bearish"): (
        "range_breakdown_risk",
        "Weekly consolidating + Daily bearish = Breakdown risk. Avoid longs until daily stabilizes.",
    ),
    ("bearish", "bullish"): (
        "bearish_bounce_sell",
        "Weekly bearish + Daily bullish = Counter-trend bounce. High risk for longs. Potential short opportunity.",
    ),
    ("bearish", "consolidating"): (
        "bearish_pause",
        "Weekly bearish + Daily consolidating = Pause in downtrend. Likely to resume decline. Avoid longs.",
    ),
    ("bearish", "bearish"): (
        "strong_bearish",
        "Weekly and daily both bearish = Strong downtrend. Stay away or look for short opportunities.",
    ),
}


class MultiTFTechnicalModule:
    """Multi-timeframe technical analysis for US stocks."""

    # Thresholds
    VOLUME_HEAVY_RATIO = 1.5
    VOLUME_SHRINK_RATIO = 0.7
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30

    def analyze(self, code: str, daily_df: pd.DataFrame) -> Optional[MultiTFResult]:
        """
        Run multi-timeframe technical analysis.

        Args:
            code: Stock ticker
            daily_df: DataFrame with daily OHLCV data. Columns: date, open, high, low, close, volume

        Returns:
            MultiTFResult or None if insufficient data
        """
        if daily_df is None or len(daily_df) < 30:
            logger.warning(f"[{code}] Insufficient data for multi-TF analysis (need 30+ daily bars)")
            return None

        result = MultiTFResult()

        # Ensure DataFrame is sorted by date
        df = daily_df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

        current_price = float(df["close"].iloc[-1])
        result.key_levels["current"] = current_price

        # Latest day's price change %
        if len(df) >= 2:
            prev_close = float(df["close"].iloc[-2])
            if prev_close > 0:
                result.latest_1d_chg_pct = (current_price - prev_close) / prev_close * 100

        # Weekly analysis
        weekly_df = self._resample_to_weekly(df)
        if len(weekly_df) >= 5:
            self._analyze_weekly(weekly_df, result)
        else:
            result.weekly_trend = "unknown"
            logger.debug(f"[{code}] Not enough weekly bars ({len(weekly_df)}), need 5+")

        # Daily analysis
        self._analyze_daily(df, result)

        # Cycle resonance
        self._determine_resonance(result)

        # Key price levels and risk-reward
        self._calculate_key_levels(df, weekly_df, result)
        self._calculate_risk_reward(result)

        # Composite score
        self._calculate_score(result)

        return result

    def _resample_to_weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample daily OHLCV to weekly bars."""
        if "date" not in df.columns:
            logger.warning("No 'date' column found for weekly resampling")
            return pd.DataFrame()

        weekly = df.set_index("date").resample("W").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        )
        weekly = weekly.dropna(subset=["close"])
        weekly = weekly.reset_index()
        return weekly

    # ── Weekly Analysis ─────────────────────────────────────────────────

    def _analyze_weekly(self, weekly_df: pd.DataFrame, result: MultiTFResult) -> None:
        """Analyze weekly timeframe: MA trend, MACD status."""
        df = weekly_df.copy()

        # Calculate weekly MAs (use min_periods to allow partial windows for short data)
        n = len(df)
        df["MA10"] = df["close"].rolling(min(10, n), min_periods=min(5, n)).mean()
        df["MA20"] = df["close"].rolling(min(20, n), min_periods=min(10, n)).mean()
        if n >= 50:
            df["MA50"] = df["close"].rolling(50).mean()
        else:
            df["MA50"] = df["MA20"]

        latest = df.iloc[-1]
        ma10 = float(latest["MA10"]) if pd.notna(latest["MA10"]) else 0
        ma20 = float(latest["MA20"]) if pd.notna(latest["MA20"]) else 0
        ma50 = float(latest["MA50"]) if pd.notna(latest["MA50"]) else 0
        price = float(latest["close"])

        # Weekly trend
        if ma10 > 0 and ma20 > 0 and ma50 > 0:
            if ma10 > ma20 > ma50:
                result.weekly_trend = "bullish"
                result.weekly_ma_alignment = "MA10>MA20>MA50"
            elif ma10 < ma20 < ma50:
                result.weekly_trend = "bearish"
                result.weekly_ma_alignment = "MA10<MA20<MA50"
            else:
                result.weekly_trend = "consolidating"
                result.weekly_ma_alignment = "mixed"

        # Price position vs weekly MAs
        if ma10 > 0:
            if price > ma10:
                result.weekly_price_vs_ma = "above_ma10"
            elif price > ma20:
                result.weekly_price_vs_ma = "between_ma10_ma20"
            elif price > ma50:
                result.weekly_price_vs_ma = "between_ma20_ma50"
            else:
                result.weekly_price_vs_ma = "below_ma50"

        # Weekly MACD
        self._calculate_macd_status(df, "weekly", result)

    def _calculate_macd_status(
        self, df: pd.DataFrame, timeframe: str, result: MultiTFResult
    ) -> None:
        """Calculate MACD status for a given timeframe."""
        if len(df) < 26:
            return

        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_bar = (dif - dea) * 2

        curr_dif = float(dif.iloc[-1])
        curr_dea = float(dea.iloc[-1])
        prev_dif = float(dif.iloc[-2])
        prev_dea = float(dea.iloc[-2])

        prev_diff = prev_dif - prev_dea
        curr_diff = curr_dif - curr_dea

        # Determine status
        if prev_diff <= 0 and curr_diff > 0:
            status = "golden_cross"
        elif prev_diff >= 0 and curr_diff < 0:
            status = "death_cross"
        elif curr_dif > 0 and curr_dea > 0:
            status = "bullish"
        elif curr_dif < 0 and curr_dea < 0:
            status = "bearish"
        else:
            status = "neutral"

        # MACD bar trend
        curr_bar = float(macd_bar.iloc[-1])
        prev_bar = float(macd_bar.iloc[-2])
        bar_trend = "expanding" if abs(curr_bar) > abs(prev_bar) else "contracting"

        if timeframe == "weekly":
            result.weekly_macd_status = status
            result.weekly_macd_bar_trend = bar_trend
        else:
            result.daily_macd_status = status

    # ── Daily Analysis ──────────────────────────────────────────────────

    def _analyze_daily(self, df: pd.DataFrame, result: MultiTFResult) -> None:
        """Analyze daily timeframe: MAs, RSI, Bollinger, MACD, volume."""
        daily = df.copy()

        # MAs
        daily["MA5"] = daily["close"].rolling(5).mean()
        daily["MA10"] = daily["close"].rolling(10).mean()
        daily["MA20"] = daily["close"].rolling(20).mean()

        latest = daily.iloc[-1]
        ma5 = float(latest["MA5"]) if pd.notna(latest["MA5"]) else 0
        ma10 = float(latest["MA10"]) if pd.notna(latest["MA10"]) else 0
        ma20 = float(latest["MA20"]) if pd.notna(latest["MA20"]) else 0

        # Daily trend
        if ma5 > 0 and ma10 > 0 and ma20 > 0:
            if ma5 > ma10 > ma20:
                result.daily_trend = "bullish"
                result.daily_ma_alignment = "MA5>MA10>MA20"
            elif ma5 < ma10 < ma20:
                result.daily_trend = "bearish"
                result.daily_ma_alignment = "MA5<MA10<MA20"
            elif ma5 > ma10 and ma10 <= ma20:
                result.daily_trend = "consolidating"
                result.daily_ma_alignment = "MA5>MA10, MA10<=MA20 (short bullish, mid neutral)"
            elif ma5 < ma10 and ma10 >= ma20:
                result.daily_trend = "consolidating"
                result.daily_ma_alignment = "MA5<MA10, MA10>=MA20 (short bearish, mid neutral)"
            else:
                result.daily_trend = "consolidating"
                result.daily_ma_alignment = "mixed"

        # RSI (14-period)
        self._calculate_rsi(daily, result)

        # Bollinger Bands (20, 2)
        self._calculate_bollinger(daily, result)

        # Daily MACD
        self._calculate_macd_status(daily, "daily", result)

        # Volume
        self._analyze_volume(daily, result)

    def _calculate_rsi(self, df: pd.DataFrame, result: MultiTFResult) -> None:
        """Calculate RSI(14) for daily timeframe."""
        if len(df) < 15:
            return

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)

        result.daily_rsi = float(rsi.iloc[-1])

        if result.daily_rsi > self.RSI_OVERBOUGHT:
            result.daily_rsi_signal = "overbought"
        elif result.daily_rsi > 60:
            result.daily_rsi_signal = "strong"
        elif result.daily_rsi >= 40:
            result.daily_rsi_signal = "neutral"
        elif result.daily_rsi >= self.RSI_OVERSOLD:
            result.daily_rsi_signal = "weak"
        else:
            result.daily_rsi_signal = "oversold"

    def _calculate_bollinger(self, df: pd.DataFrame, result: MultiTFResult) -> None:
        """Calculate Bollinger Bands (20, 2) and determine price position."""
        if len(df) < 20:
            return

        ma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20

        latest_close = float(df["close"].iloc[-1])
        latest_upper = float(upper.iloc[-1])
        latest_lower = float(lower.iloc[-1])
        latest_ma20 = float(ma20.iloc[-1])

        if latest_ma20 > 0:
            result.daily_bollinger_bandwidth = (latest_upper - latest_lower) / latest_ma20 * 100

        if latest_close > latest_upper:
            result.daily_bollinger_position = "above_upper"
        elif latest_close > latest_ma20:
            result.daily_bollinger_position = "upper_half"
        elif latest_close > latest_lower:
            result.daily_bollinger_position = "lower_half"
        else:
            result.daily_bollinger_position = "below_lower"

    def _analyze_volume(self, df: pd.DataFrame, result: MultiTFResult) -> None:
        """Analyze volume relative to 5-day and 20-day averages."""
        if len(df) < 6:
            return

        latest_vol = float(df["volume"].iloc[-1])
        avg_vol_5d = float(df["volume"].iloc[-6:-1].mean())

        if avg_vol_5d > 0:
            result.daily_volume_ratio = latest_vol / avg_vol_5d

        # Determine price direction
        prev_close = float(df["close"].iloc[-2])
        curr_close = float(df["close"].iloc[-1])
        price_up = curr_close > prev_close

        if result.daily_volume_ratio >= self.VOLUME_HEAVY_RATIO:
            result.daily_volume_signal = "heavy_up" if price_up else "heavy_down"
        elif result.daily_volume_ratio <= self.VOLUME_SHRINK_RATIO:
            result.daily_volume_signal = "shrink_up" if price_up else "shrink_down"
        else:
            result.daily_volume_signal = "normal"

    # ── Cycle Resonance ─────────────────────────────────────────────────

    def _determine_resonance(self, result: MultiTFResult) -> None:
        """Determine cycle resonance from weekly + daily trend combination."""
        weekly = result.weekly_trend
        daily = result.daily_trend

        key = (weekly, daily)
        if key in RESONANCE_MATRIX:
            result.cycle_resonance, result.resonance_description = RESONANCE_MATRIX[key]
        else:
            result.cycle_resonance = "undefined"
            result.resonance_description = f"Weekly {weekly} + Daily {daily}: No clear signal."

    # ── Key Levels & Risk-Reward ────────────────────────────────────────

    def _calculate_key_levels(
        self, daily_df: pd.DataFrame, weekly_df: pd.DataFrame, result: MultiTFResult
    ) -> None:
        """Calculate key support and resistance levels."""
        current = result.key_levels.get("current", 0)
        if current == 0:
            return

        # Support levels
        supports = []

        # Daily MAs as support
        daily = daily_df.copy()
        daily["MA5"] = daily["close"].rolling(5).mean()
        daily["MA10"] = daily["close"].rolling(10).mean()
        daily["MA20"] = daily["close"].rolling(20).mean()

        for ma_name in ["MA5", "MA10", "MA20"]:
            if pd.notna(daily[ma_name].iloc[-1]):
                ma_val = float(daily[ma_name].iloc[-1])
                if ma_val < current:
                    supports.append((ma_name, ma_val))

        # Recent swing low (20-day)
        if len(daily) >= 20:
            recent_low = float(daily["low"].iloc[-20:].min())
            if recent_low < current:
                supports.append(("20d_low", recent_low))

        # Resistance levels
        resistances = []

        # Recent swing high (20-day)
        if len(daily) >= 20:
            recent_high = float(daily["high"].iloc[-20:].max())
            if recent_high > current:
                resistances.append(("20d_high", recent_high))

        # 52-week high approximation (if enough data)
        if len(daily) >= 200:
            high_200d = float(daily["high"].iloc[-200:].max())
            if high_200d > current and high_200d != resistances[0][1] if resistances else True:
                resistances.append(("200d_high", high_200d))

        # Weekly MA as potential resistance (if price is below)
        if len(weekly_df) >= 20:
            wk_ma20 = weekly_df["close"].rolling(20).mean()
            if pd.notna(wk_ma20.iloc[-1]):
                wk_ma20_val = float(wk_ma20.iloc[-1])
                if wk_ma20_val > current:
                    resistances.append(("weekly_MA20", wk_ma20_val))

        # Store sorted levels
        supports.sort(key=lambda x: x[1], reverse=True)  # nearest support first
        resistances.sort(key=lambda x: x[1])  # nearest resistance first

        if supports:
            result.key_levels["support_1"] = supports[0][1]
            result.key_levels["support_1_name"] = supports[0][0]
            if len(supports) > 1:
                result.key_levels["support_2"] = supports[1][1]
                result.key_levels["support_2_name"] = supports[1][0]

        if resistances:
            result.key_levels["resistance_1"] = resistances[0][1]
            result.key_levels["resistance_1_name"] = resistances[0][0]
            if len(resistances) > 1:
                result.key_levels["resistance_2"] = resistances[1][1]
                result.key_levels["resistance_2_name"] = resistances[1][0]

    def _calculate_risk_reward(self, result: MultiTFResult) -> None:
        """Calculate risk-reward ratio based on key levels."""
        current = result.key_levels.get("current", 0)
        resistance = result.key_levels.get("resistance_1", 0)
        support = result.key_levels.get("support_1", 0)

        if current > 0 and support > 0 and resistance > 0:
            upside = resistance - current
            downside = current - support
            if downside > 0:
                result.risk_reward_ratio = upside / downside
            else:
                result.risk_reward_ratio = 0

    # ── Composite Score ─────────────────────────────────────────────────

    def _calculate_score(self, result: MultiTFResult) -> None:
        """
        Calculate composite technical score (0-100).

        Scoring breakdown:
        - Weekly trend (25 pts)
        - Daily trend (15 pts)
        - Cycle resonance (20 pts)
        - RSI (10 pts)
        - Volume (10 pts)
        - MACD alignment (10 pts)
        - Risk-reward ratio (10 pts)
        """
        score = 0

        # Weekly trend (25 pts)
        weekly_scores = {"bullish": 25, "consolidating": 12, "bearish": 0, "unknown": 10}
        score += weekly_scores.get(result.weekly_trend, 10)

        # Daily trend (15 pts)
        daily_scores = {"bullish": 15, "consolidating": 8, "bearish": 0, "unknown": 6}
        score += daily_scores.get(result.daily_trend, 6)

        # Cycle resonance (20 pts)
        resonance_scores = {
            "strong_bullish": 20,
            "bullish_pullback_buy": 17,
            "bullish_correction": 12,
            "range_breakout_attempt": 13,
            "range_bound": 10,
            "range_breakdown_risk": 5,
            "bearish_bounce_sell": 4,
            "bearish_pause": 2,
            "strong_bearish": 0,
        }
        score += resonance_scores.get(result.cycle_resonance, 8)

        # RSI (10 pts) - best when neutral-to-strong, not overbought
        rsi_scores = {
            "oversold": 8,
            "weak": 5,
            "neutral": 7,
            "strong": 10,
            "overbought": 3,
        }
        score += rsi_scores.get(result.daily_rsi_signal, 5)

        # Volume (10 pts)
        volume_scores = {
            "shrink_down": 8,  # pullback on low volume = healthy
            "heavy_up": 10,  # breakout volume
            "normal": 6,
            "shrink_up": 4,  # rally without conviction
            "heavy_down": 0,  # selling pressure
        }
        score += volume_scores.get(result.daily_volume_signal, 5)

        # MACD alignment (10 pts) - reward when both weekly and daily are bullish
        macd_score = 0
        if result.weekly_macd_status in ("golden_cross", "bullish"):
            macd_score += 5
        elif result.weekly_macd_status == "neutral":
            macd_score += 2
        if result.daily_macd_status in ("golden_cross", "bullish"):
            macd_score += 5
        elif result.daily_macd_status == "neutral":
            macd_score += 2
        score += macd_score

        # Risk-reward ratio (10 pts)
        rr = result.risk_reward_ratio
        if rr >= 3:
            score += 10
        elif rr >= 2:
            score += 8
        elif rr >= 1.5:
            score += 6
        elif rr >= 1:
            score += 4
        elif rr > 0:
            score += 2

        result.score = min(100, max(0, score))
