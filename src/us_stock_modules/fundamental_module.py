# -*- coding: utf-8 -*-
"""
Module 3: Fundamental Snapshot

Evaluates a US stock's fundamental health using yfinance Ticker.info:
- Valuation: PE, forward PE, PEG, P/S
- Growth: revenue growth, earnings growth
- Margins: gross, operating, profit
- Financial health: free cash flow, debt/equity, current ratio
- Institutional ownership percentage

All data sourced from yfinance (free).
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class FundamentalResult:
    """Fundamental analysis result."""

    # Valuation
    pe_ttm: Optional[float] = None
    pe_forward: Optional[float] = None
    peg: Optional[float] = None
    ps_ttm: Optional[float] = None

    # Growth
    revenue_growth_yoy: Optional[float] = None  # as decimal (0.24 = 24%)
    earnings_growth_yoy: Optional[float] = None

    # Margins
    gross_margin: Optional[float] = None  # as decimal (0.52 = 52%)
    operating_margin: Optional[float] = None
    profit_margin: Optional[float] = None

    # Financial health
    free_cashflow: Optional[float] = None  # absolute value in USD
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None

    # Institutional
    institutional_pct: Optional[float] = None  # as percentage (76.2 = 76.2%)

    # Scores
    score: int = 50
    valuation_signal: str = "unknown"  # "cheap" / "fair" / "expensive"
    growth_signal: str = "unknown"  # "high_growth" / "moderate" / "declining" / "negative"

    def to_dict(self) -> Dict[str, Any]:
        def _pct(v):
            """Convert decimal to percentage for display."""
            if v is None:
                return None
            return round(v * 100, 2)

        return {
            "pe_ttm": round(self.pe_ttm, 2) if self.pe_ttm else None,
            "pe_forward": round(self.pe_forward, 2) if self.pe_forward else None,
            "peg": round(self.peg, 2) if self.peg else None,
            "ps_ttm": round(self.ps_ttm, 2) if self.ps_ttm else None,
            "revenue_growth_yoy": _pct(self.revenue_growth_yoy),
            "earnings_growth_yoy": _pct(self.earnings_growth_yoy),
            "gross_margin": _pct(self.gross_margin),
            "operating_margin": _pct(self.operating_margin),
            "profit_margin": _pct(self.profit_margin),
            "free_cashflow": self.free_cashflow,
            "debt_to_equity": round(self.debt_to_equity, 2) if self.debt_to_equity else None,
            "current_ratio": round(self.current_ratio, 2) if self.current_ratio else None,
            "institutional_pct": round(self.institutional_pct, 2) if self.institutional_pct else None,
            "score": self.score,
            "valuation_signal": self.valuation_signal,
            "growth_signal": self.growth_signal,
        }


class FundamentalModule:
    """Fundamental analysis using yfinance Ticker.info data."""

    def analyze(self, code: str) -> Optional[FundamentalResult]:
        """
        Fetch and score fundamental data for a US stock.

        Args:
            code: US stock ticker (e.g. "AAPL")

        Returns:
            FundamentalResult or None if data unavailable
        """
        try:
            from src.us_stock_modules.yf_utils import yf_ticker_info

            info = yf_ticker_info(code)

            if not info or len(info) < 5:
                logger.warning(f"[{code}] No fundamental data available from yfinance")
                return None

            result = FundamentalResult()

            # Extract valuation metrics
            result.pe_ttm = self._safe_float(info.get("trailingPE"))
            result.pe_forward = self._safe_float(info.get("forwardPE"))
            result.peg = self._safe_float(info.get("pegRatio"))
            result.ps_ttm = self._safe_float(info.get("priceToSalesTrailing12Months"))

            # Extract growth metrics (yfinance returns as decimal)
            result.revenue_growth_yoy = self._safe_float(info.get("revenueGrowth"))
            result.earnings_growth_yoy = self._safe_float(info.get("earningsGrowth"))

            # Extract margin metrics (yfinance returns as decimal)
            result.gross_margin = self._safe_float(info.get("grossMargins"))
            result.operating_margin = self._safe_float(info.get("operatingMargins"))
            result.profit_margin = self._safe_float(info.get("profitMargins"))

            # Extract financial health
            result.free_cashflow = self._safe_float(info.get("freeCashflow"))
            result.debt_to_equity = self._safe_float(info.get("debtToEquity"))
            result.current_ratio = self._safe_float(info.get("currentRatio"))

            # Institutional ownership
            held_pct = self._safe_float(info.get("heldPercentInstitutions"))
            if held_pct is not None:
                result.institutional_pct = held_pct * 100  # Convert from decimal to percentage

            # Score the fundamentals
            self._calculate_scores(result)

            logger.info(
                f"[{code}] Fundamental: PE={result.pe_ttm}, PEG={result.peg}, "
                f"RevGrowth={result.revenue_growth_yoy}, score={result.score}"
            )
            return result

        except ImportError:
            logger.error("yfinance not installed, cannot run fundamental analysis")
            return None
        except Exception as e:
            logger.warning(f"[{code}] Fundamental analysis failed: {e}")
            return None

    def _calculate_scores(self, result: FundamentalResult) -> None:
        """Calculate valuation signal, growth signal, and composite score."""
        scores = []
        weights = []

        # Valuation score (30% weight)
        val_score = self._score_valuation(result)
        scores.append(val_score)
        weights.append(30)

        # Growth score (30% weight)
        growth_score = self._score_growth(result)
        scores.append(growth_score)
        weights.append(30)

        # Margins score (20% weight)
        margin_score = self._score_margins(result)
        scores.append(margin_score)
        weights.append(20)

        # Financial health score (20% weight)
        health_score = self._score_health(result)
        scores.append(health_score)
        weights.append(20)

        # Weighted total
        total_weight = sum(weights)
        if total_weight > 0:
            result.score = int(round(sum(s * w for s, w in zip(scores, weights)) / total_weight))
        else:
            result.score = 50

        result.score = min(100, max(0, result.score))

    def _score_valuation(self, result: FundamentalResult) -> int:
        """Score valuation metrics (0-100)."""
        peg = result.peg
        pe = result.pe_ttm

        if peg is not None and peg > 0:
            # PEG-based valuation
            if peg < 0.8:
                result.valuation_signal = "cheap"
                return 90
            elif peg < 1.0:
                result.valuation_signal = "cheap"
                return 80
            elif peg < 1.5:
                result.valuation_signal = "fair"
                return 65
            elif peg < 2.0:
                result.valuation_signal = "fair"
                return 50
            elif peg < 3.0:
                result.valuation_signal = "expensive"
                return 35
            else:
                result.valuation_signal = "expensive"
                return 20
        elif pe is not None and pe > 0:
            # PE-based fallback
            if pe < 12:
                result.valuation_signal = "cheap"
                return 85
            elif pe < 20:
                result.valuation_signal = "fair"
                return 70
            elif pe < 30:
                result.valuation_signal = "fair"
                return 55
            elif pe < 50:
                result.valuation_signal = "expensive"
                return 35
            else:
                result.valuation_signal = "expensive"
                return 20
        else:
            result.valuation_signal = "unknown"
            return 50

    def _score_growth(self, result: FundamentalResult) -> int:
        """Score growth metrics (0-100)."""
        rev = result.revenue_growth_yoy
        earn = result.earnings_growth_yoy

        # Use the better of revenue or earnings growth
        growth = None
        if rev is not None and earn is not None:
            growth = max(rev, earn)
        elif rev is not None:
            growth = rev
        elif earn is not None:
            growth = earn

        if growth is None:
            result.growth_signal = "unknown"
            return 50

        if growth > 0.50:
            result.growth_signal = "high_growth"
            return 95
        elif growth > 0.25:
            result.growth_signal = "high_growth"
            return 80
        elif growth > 0.10:
            result.growth_signal = "moderate"
            return 65
        elif growth > 0:
            result.growth_signal = "moderate"
            return 55
        elif growth > -0.10:
            result.growth_signal = "declining"
            return 35
        else:
            result.growth_signal = "negative"
            return 15

    def _score_margins(self, result: FundamentalResult) -> int:
        """Score margin metrics (0-100)."""
        gm = result.gross_margin

        if gm is None:
            return 50

        # Higher margins = better
        if gm > 0.60:
            return 90
        elif gm > 0.45:
            return 75
        elif gm > 0.30:
            return 60
        elif gm > 0.15:
            return 45
        elif gm > 0:
            return 30
        else:
            return 15

    def _score_health(self, result: FundamentalResult) -> int:
        """Score financial health (0-100)."""
        dte = result.debt_to_equity
        fcf = result.free_cashflow

        scores = []

        # Debt/equity
        if dte is not None:
            if dte < 30:
                scores.append(90)
            elif dte < 50:
                scores.append(75)
            elif dte < 100:
                scores.append(55)
            elif dte < 200:
                scores.append(35)
            else:
                scores.append(15)

        # Free cash flow (positive is good)
        if fcf is not None:
            if fcf > 0:
                scores.append(80)
            else:
                scores.append(25)

        if scores:
            return int(round(sum(scores) / len(scores)))
        return 50

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert a value to float."""
        if value is None:
            return None
        try:
            v = float(value)
            # Filter out obviously wrong values
            if v != v:  # NaN check
                return None
            return v
        except (TypeError, ValueError):
            return None
