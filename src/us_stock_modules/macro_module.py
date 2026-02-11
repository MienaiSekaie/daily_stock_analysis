# -*- coding: utf-8 -*-
"""
Module 1: Macro Environment (Market Regime)

Evaluates overall US market conditions using:
- SPY vs MA50 (broad market trend)
- VIX (fear/greed)
- 10Y Treasury yield (rate environment)
- DXY Dollar index (currency strength)

All data sourced from yfinance (free).
Results are cached since macro data is shared across all stocks in a batch.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class MacroResult:
    """Macro environment analysis result."""

    spy_vs_ma50_pct: float = 0.0
    spy_trend: str = "unknown"  # "above_ma50" / "below_ma50"
    spy_price: float = 0.0

    vix: float = 0.0
    vix_signal: str = "unknown"  # "calm" / "elevated" / "panic"

    us10y_yield: float = 0.0
    us10y_signal: str = "unknown"  # "low" / "moderate" / "high"

    dxy: float = 0.0
    dxy_signal: str = "unknown"  # "weak" / "neutral" / "strong"

    market_regime: str = "unknown"  # "offensive" / "defensive" / "risk_off"
    score: int = 50
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spy_vs_ma50_pct": round(self.spy_vs_ma50_pct, 2),
            "spy_trend": self.spy_trend,
            "spy_price": round(self.spy_price, 2),
            "vix": round(self.vix, 2),
            "vix_signal": self.vix_signal,
            "us10y_yield": round(self.us10y_yield, 2),
            "us10y_signal": self.us10y_signal,
            "dxy": round(self.dxy, 2),
            "dxy_signal": self.dxy_signal,
            "market_regime": self.market_regime,
            "score": self.score,
            "details": self.details,
        }


class MacroModule:
    """
    Macro environment analyzer.

    Fetches SPY, VIX, 10Y yield, and DXY via yfinance.
    Uses class-level cache so batch analyses share the same macro data.
    """

    # Class-level cache shared across instances
    _cache: Optional[MacroResult] = None
    _cache_time: Optional[float] = None
    _cache_ttl: int = 3600  # default 1 hour

    def __init__(self, cache_ttl: int = 3600):
        MacroModule._cache_ttl = cache_ttl

    def analyze(self) -> Optional[MacroResult]:
        """
        Fetch macro data and compute market regime score.

        Returns:
            MacroResult or None if data fetch fails completely
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("Using cached macro data")
            return MacroModule._cache

        try:
            from src.us_stock_modules.yf_utils import yf_download

            result = MacroResult()
            scores = {}

            # 1. SPY vs MA50 (25% weight)
            try:
                spy_data = yf_download("SPY", period="4mo")
                if spy_data is not None and len(spy_data) >= 50:
                    spy_close = spy_data["Close"]
                    ma50 = spy_close.rolling(50).mean()
                    latest_price = float(spy_close.iloc[-1])
                    latest_ma50 = float(ma50.iloc[-1])

                    result.spy_price = latest_price
                    if latest_ma50 > 0:
                        result.spy_vs_ma50_pct = (latest_price - latest_ma50) / latest_ma50 * 100
                    result.spy_trend = "above_ma50" if latest_price > latest_ma50 else "below_ma50"

                    # Score: above MA50 and rising = good
                    pct = result.spy_vs_ma50_pct
                    if pct > 5:
                        scores["spy"] = 90
                    elif pct > 2:
                        scores["spy"] = 80
                    elif pct > 0:
                        scores["spy"] = 65
                    elif pct > -2:
                        scores["spy"] = 45
                    elif pct > -5:
                        scores["spy"] = 30
                    else:
                        scores["spy"] = 15
            except Exception as e:
                logger.warning(f"Failed to fetch SPY data: {e}")
                scores["spy"] = 50

            # 2. VIX (25% weight)
            try:
                vix_data = yf_download("^VIX", period="5d")
                if vix_data is not None and len(vix_data) > 0:
                    result.vix = float(vix_data["Close"].iloc[-1])

                    if result.vix < 15:
                        result.vix_signal = "calm"
                        scores["vix"] = 90
                    elif result.vix < 20:
                        result.vix_signal = "calm"
                        scores["vix"] = 75
                    elif result.vix < 25:
                        result.vix_signal = "elevated"
                        scores["vix"] = 55
                    elif result.vix < 30:
                        result.vix_signal = "elevated"
                        scores["vix"] = 35
                    elif result.vix < 35:
                        result.vix_signal = "panic"
                        scores["vix"] = 20
                    else:
                        result.vix_signal = "panic"
                        scores["vix"] = 10
            except Exception as e:
                logger.warning(f"Failed to fetch VIX data: {e}")
                scores["vix"] = 50

            # 3. 10Y Treasury Yield (25% weight)
            try:
                tnx_data = yf_download("^TNX", period="5d")
                if tnx_data is not None and len(tnx_data) > 0:
                    result.us10y_yield = float(tnx_data["Close"].iloc[-1])

                    # Lower yields generally better for stocks
                    yld = result.us10y_yield
                    if yld < 3.5:
                        result.us10y_signal = "low"
                        scores["us10y"] = 85
                    elif yld < 4.0:
                        result.us10y_signal = "moderate"
                        scores["us10y"] = 70
                    elif yld < 4.5:
                        result.us10y_signal = "moderate"
                        scores["us10y"] = 55
                    elif yld < 5.0:
                        result.us10y_signal = "high"
                        scores["us10y"] = 35
                    else:
                        result.us10y_signal = "high"
                        scores["us10y"] = 20
            except Exception as e:
                logger.warning(f"Failed to fetch 10Y yield data: {e}")
                scores["us10y"] = 50

            # 4. DXY Dollar Index (25% weight)
            try:
                dxy_data = yf_download("DX-Y.NYB", period="5d")
                if dxy_data is not None and len(dxy_data) > 0:
                    result.dxy = float(dxy_data["Close"].iloc[-1])

                    # Strong dollar generally headwind for stocks
                    dxy = result.dxy
                    if dxy < 98:
                        result.dxy_signal = "weak"
                        scores["dxy"] = 80
                    elif dxy < 102:
                        result.dxy_signal = "neutral"
                        scores["dxy"] = 65
                    elif dxy < 105:
                        result.dxy_signal = "neutral"
                        scores["dxy"] = 50
                    elif dxy < 108:
                        result.dxy_signal = "strong"
                        scores["dxy"] = 35
                    else:
                        result.dxy_signal = "strong"
                        scores["dxy"] = 20
            except Exception as e:
                logger.warning(f"Failed to fetch DXY data: {e}")
                scores["dxy"] = 50

            # Compute weighted score
            weights = {"spy": 25, "vix": 25, "us10y": 25, "dxy": 25}
            total_weight = sum(weights.get(k, 0) for k in scores)
            if total_weight > 0:
                weighted_sum = sum(scores.get(k, 50) * weights.get(k, 0) for k in scores)
                result.score = int(round(weighted_sum / total_weight))
            else:
                result.score = 50

            # Determine market regime
            if result.score >= 70:
                result.market_regime = "offensive"
            elif result.score >= 45:
                result.market_regime = "defensive"
            else:
                result.market_regime = "risk_off"

            result.details = {k: {"score": v, "weight": weights.get(k, 0)} for k, v in scores.items()}

            # Update cache
            MacroModule._cache = result
            MacroModule._cache_time = time.time()

            logger.info(
                f"Macro analysis: regime={result.market_regime}, score={result.score}, "
                f"SPY={result.spy_vs_ma50_pct:+.1f}% vs MA50, VIX={result.vix:.1f}"
            )
            return result

        except ImportError:
            logger.error("yfinance not installed, cannot run macro analysis")
            return None
        except Exception as e:
            logger.error(f"Macro analysis failed: {e}")
            return None

    @classmethod
    def _is_cache_valid(cls) -> bool:
        """Check if cached macro data is still fresh."""
        if cls._cache is None or cls._cache_time is None:
            return False
        return (time.time() - cls._cache_time) < cls._cache_ttl
