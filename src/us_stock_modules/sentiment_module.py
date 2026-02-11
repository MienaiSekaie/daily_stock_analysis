# -*- coding: utf-8 -*-
"""
Module 6: Sentiment & Flow

Evaluates market sentiment and institutional positioning:
- Analyst ratings consensus (Buy/Hold/Sell distribution)
- Analyst price targets (upside/downside potential)
- Institutional holders (top holders, ownership %)
- News sentiment (keyword-based scoring from existing news context)

Data sources (yfinance only, no Reddit/Stocktwits APIs):
- Analyst ratings: yf.Ticker.recommendations
- Price targets: yf.Ticker.info (targetMeanPrice, etc.)
- Institutional: yf.Ticker.institutional_holders
- News: keyword analysis on pre-fetched news_context string
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Keyword lists for basic news sentiment scoring
POSITIVE_KEYWORDS = [
    "beat", "beats", "exceeded", "surpass", "upgrade", "upgraded", "outperform",
    "bullish", "rally", "surge", "soar", "gain", "gains", "record", "strong",
    "growth", "profitable", "dividend", "buyback", "expansion", "innovative",
    "breakthrough", "optimistic", "positive", "upside", "buy", "accumulate",
    "overweight", "above expectations", "better than expected", "raised guidance",
    "all-time high", "market leader",
]

NEGATIVE_KEYWORDS = [
    "miss", "missed", "below", "downgrade", "downgraded", "underperform",
    "bearish", "decline", "drop", "fall", "loss", "losses", "weak", "warning",
    "layoff", "layoffs", "restructuring", "lawsuit", "investigation", "recall",
    "negative", "downside", "sell", "underweight", "reduce", "below expectations",
    "worse than expected", "lowered guidance", "cut guidance", "bankruptcy",
    "debt concern", "margin pressure",
]


@dataclass
class SentimentResult:
    """Sentiment & flow analysis result."""

    # Analyst ratings
    analyst_buy: int = 0
    analyst_hold: int = 0
    analyst_sell: int = 0
    analyst_total: int = 0
    analyst_consensus: str = ""  # "strong_buy" / "buy" / "hold" / "sell" / "strong_sell"

    # Price targets
    target_mean: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    target_upside_pct: Optional[float] = None  # % upside to mean target
    num_analysts: Optional[int] = None

    # Institutional ownership
    institutional_pct: Optional[float] = None  # Total institutional ownership %
    top_holders: List[Dict[str, Any]] = field(default_factory=list)  # Top 5 holders

    # News sentiment
    news_positive_count: int = 0
    news_negative_count: int = 0
    news_sentiment: str = ""  # "positive" / "neutral" / "negative"

    score: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyst_buy": self.analyst_buy,
            "analyst_hold": self.analyst_hold,
            "analyst_sell": self.analyst_sell,
            "analyst_total": self.analyst_total,
            "analyst_consensus": self.analyst_consensus,
            "target_mean": round(self.target_mean, 2) if self.target_mean is not None else None,
            "target_high": round(self.target_high, 2) if self.target_high is not None else None,
            "target_low": round(self.target_low, 2) if self.target_low is not None else None,
            "target_upside_pct": round(self.target_upside_pct, 2) if self.target_upside_pct is not None else None,
            "num_analysts": self.num_analysts,
            "institutional_pct": round(self.institutional_pct, 2) if self.institutional_pct is not None else None,
            "top_holders": self.top_holders,
            "news_positive_count": self.news_positive_count,
            "news_negative_count": self.news_negative_count,
            "news_sentiment": self.news_sentiment,
            "score": self.score,
        }


class SentimentModule:
    """Sentiment & flow analyzer using yfinance data."""

    def analyze(self, code: str, news_context: Optional[str] = None) -> Optional[SentimentResult]:
        """
        Analyze sentiment from analyst ratings, price targets, institutional holders,
        and news keyword analysis.

        Args:
            code: US stock ticker
            news_context: Pre-formatted news text from SearchService

        Returns:
            SentimentResult or None
        """
        try:
            result = SentimentResult()

            # 1. News sentiment (no API call needed)
            if news_context:
                self._analyze_news_sentiment(news_context, result)

            # 2. yfinance-based data
            try:
                from src.us_stock_modules.yf_utils import yf_ticker, yf_ticker_info
                ticker = yf_ticker(code)
                info = yf_ticker_info(code) if ticker else {}

                if ticker is not None:
                    # 2a. Analyst ratings
                    self._analyze_analyst_ratings(ticker, code, result)

                # 2b. Price targets
                self._analyze_price_targets(info, code, result)

                if ticker is not None:
                    # 2c. Institutional holders
                    self._analyze_institutional(ticker, info, code, result)

            except ImportError:
                logger.warning("yfinance not installed, skipping analyst/institutional data")

            # Score
            self._calculate_score(result)

            logger.info(
                f"[{code}] Sentiment: consensus={result.analyst_consensus}, "
                f"target_upside={result.target_upside_pct}%, "
                f"news={result.news_sentiment}, score={result.score}"
            )
            return result

        except Exception as e:
            logger.warning(f"[{code}] Sentiment analysis failed: {e}")
            return None

    def _analyze_news_sentiment(self, news_context: str, result: SentimentResult) -> None:
        """Analyze news text for positive/negative keyword counts."""
        try:
            text_lower = news_context.lower()

            for keyword in POSITIVE_KEYWORDS:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                result.news_positive_count += count

            for keyword in NEGATIVE_KEYWORDS:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                result.news_negative_count += count

            total = result.news_positive_count + result.news_negative_count
            if total == 0:
                result.news_sentiment = "neutral"
            elif result.news_positive_count > result.news_negative_count * 1.5:
                result.news_sentiment = "positive"
            elif result.news_negative_count > result.news_positive_count * 1.5:
                result.news_sentiment = "negative"
            else:
                result.news_sentiment = "neutral"

        except Exception as e:
            logger.debug(f"News sentiment analysis failed: {e}")
            result.news_sentiment = "neutral"

    def _analyze_analyst_ratings(self, ticker, code: str, result: SentimentResult) -> None:
        """Extract analyst rating consensus from yfinance recommendations."""
        try:
            recs = ticker.recommendations
            if recs is None or len(recs) == 0:
                return

            import pandas as pd

            # Get recent recommendations (last 90 days)
            if hasattr(recs.index, 'tz_localize'):
                now = pd.Timestamp.now(tz=recs.index.tz) if recs.index.tz else pd.Timestamp.now()
            else:
                now = pd.Timestamp.now()

            cutoff = now - pd.Timedelta(days=90)
            recent = recs[recs.index >= cutoff] if len(recs) > 0 else recs

            if len(recent) == 0:
                # Fall back to all available data
                recent = recs.tail(20)

            # Count ratings — yfinance recommendations have different column formats
            buy_count = 0
            hold_count = 0
            sell_count = 0

            if "To Grade" in recent.columns:
                # Old format: Firm, To Grade, From Grade, Action
                for grade in recent["To Grade"].str.lower():
                    if any(kw in str(grade) for kw in ["buy", "outperform", "overweight", "accumulate", "positive"]):
                        buy_count += 1
                    elif any(kw in str(grade) for kw in ["sell", "underperform", "underweight", "negative", "reduce"]):
                        sell_count += 1
                    else:
                        hold_count += 1
            elif "strongBuy" in recent.columns:
                # New format: strongBuy, buy, hold, sell, strongSell (aggregated)
                row = recent.iloc[-1]
                buy_count = int(row.get("strongBuy", 0) or 0) + int(row.get("buy", 0) or 0)
                hold_count = int(row.get("hold", 0) or 0)
                sell_count = int(row.get("sell", 0) or 0) + int(row.get("strongSell", 0) or 0)

            result.analyst_buy = buy_count
            result.analyst_hold = hold_count
            result.analyst_sell = sell_count
            result.analyst_total = buy_count + hold_count + sell_count

            # Determine consensus
            if result.analyst_total > 0:
                buy_pct = buy_count / result.analyst_total
                sell_pct = sell_count / result.analyst_total
                if buy_pct >= 0.7:
                    result.analyst_consensus = "strong_buy"
                elif buy_pct >= 0.5:
                    result.analyst_consensus = "buy"
                elif sell_pct >= 0.5:
                    result.analyst_consensus = "sell"
                elif sell_pct >= 0.7:
                    result.analyst_consensus = "strong_sell"
                else:
                    result.analyst_consensus = "hold"

        except Exception as e:
            logger.debug(f"[{code}] Could not fetch analyst ratings: {e}")

    def _analyze_price_targets(self, info: dict, code: str, result: SentimentResult) -> None:
        """Extract analyst price targets from yfinance info."""
        try:
            result.target_mean = info.get("targetMeanPrice")
            result.target_high = info.get("targetHighPrice")
            result.target_low = info.get("targetLowPrice")
            result.num_analysts = info.get("numberOfAnalystOpinions")

            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            if result.target_mean is not None and current_price is not None and current_price > 0:
                result.target_upside_pct = ((result.target_mean - current_price) / current_price) * 100

        except Exception as e:
            logger.debug(f"[{code}] Could not fetch price targets: {e}")

    def _analyze_institutional(self, ticker, info: dict, code: str, result: SentimentResult) -> None:
        """Extract institutional holder data."""
        try:
            # Institutional ownership percentage from info
            inst_pct = info.get("heldPercentInstitutions")
            if inst_pct is not None:
                result.institutional_pct = float(inst_pct) * 100  # Convert to %

            # Top institutional holders
            try:
                holders = ticker.institutional_holders
                if holders is not None and len(holders) > 0:
                    top5 = holders.head(5)
                    for _, row in top5.iterrows():
                        holder_info = {
                            "name": str(row.get("Holder", "")),
                            "shares": int(row.get("Shares", 0)) if row.get("Shares") is not None else 0,
                            "pct": round(float(row.get("% Out", 0)) * 100, 2) if row.get("% Out") is not None else None,
                        }
                        result.top_holders.append(holder_info)
            except Exception as e:
                logger.debug(f"[{code}] Could not fetch institutional holders: {e}")

        except Exception as e:
            logger.debug(f"[{code}] Institutional analysis failed: {e}")

    def _calculate_score(self, result: SentimentResult) -> None:
        """
        Calculate sentiment score (0-100).

        Higher score = more bullish sentiment (analyst consensus, upside potential, positive news).
        Lower score = bearish sentiment.
        """
        score = 50  # Start neutral

        # Analyst consensus (weight: 35%)
        consensus_scores = {
            "strong_buy": 90,
            "buy": 75,
            "hold": 50,
            "sell": 25,
            "strong_sell": 10,
        }
        if result.analyst_consensus:
            consensus_score = consensus_scores.get(result.analyst_consensus, 50)
            score += (consensus_score - 50) * 0.35

        # Price target upside (weight: 30%)
        if result.target_upside_pct is not None:
            if result.target_upside_pct > 30:
                score += 15
            elif result.target_upside_pct > 15:
                score += 10
            elif result.target_upside_pct > 5:
                score += 5
            elif result.target_upside_pct < -15:
                score -= 15
            elif result.target_upside_pct < -5:
                score -= 10
            elif result.target_upside_pct < 0:
                score -= 5

        # Institutional ownership (weight: 15%)
        if result.institutional_pct is not None:
            if result.institutional_pct > 80:
                score += 5  # Heavily institutional = stable
            elif result.institutional_pct > 50:
                score += 3
            elif result.institutional_pct < 20:
                score -= 3  # Very low institutional interest

        # News sentiment (weight: 20%)
        news_scores = {"positive": 10, "neutral": 0, "negative": -10}
        if result.news_sentiment:
            score += news_scores.get(result.news_sentiment, 0)

        result.score = min(100, max(0, int(score)))
