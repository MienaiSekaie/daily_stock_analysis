# -*- coding: utf-8 -*-
"""
Module 6: Sentiment & Flow

Evaluates market sentiment:
- Analyst ratings consensus (Buy/Hold/Sell distribution)
- Analyst price targets (upside/downside potential)
- News sentiment via Alpha Vantage NEWS_SENTIMENT API

Data sources:
- Analyst ratings & price targets: OpenBB SDK (FMP consensus)
- News sentiment: Alpha Vantage NEWS_SENTIMENT (AI-scored per ticker)
- Fallback: keyword analysis on pre-fetched news_context string
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    """Sentiment & flow analyzer using OpenBB SDK data."""

    def analyze(self, code: str, news_context: Optional[str] = None) -> Optional[SentimentResult]:
        """
        Analyze sentiment from analyst ratings, price targets, and news.

        Uses Alpha Vantage NEWS_SENTIMENT for AI-scored news analysis,
        falling back to keyword matching on news_context if AV unavailable.

        Args:
            code: US stock ticker
            news_context: Pre-formatted news text from SearchService (fallback)

        Returns:
            SentimentResult or None
        """
        try:
            result = SentimentResult()

            # 1. News sentiment via Alpha Vantage NEWS_SENTIMENT
            av_news_used = False
            try:
                from src.us_stock_modules.openbb_utils import av_news_sentiment

                news = av_news_sentiment(code, limit=50)
                if news and news.get("total_scored", 0) > 0:
                    result.news_positive_count = news["positive_count"]
                    result.news_negative_count = news["negative_count"]
                    result.news_sentiment = news["sentiment_label"]
                    av_news_used = True
                    logger.debug(
                        f"[{code}] AV news sentiment: {news['sentiment_label']}, "
                        f"+{news['positive_count']}/-{news['negative_count']}, "
                        f"avg={news['avg_sentiment']:.3f}"
                    )
            except Exception as e:
                logger.debug(f"[{code}] AV news sentiment failed: {e}")

            # 1b. Fallback: keyword analysis on pre-fetched news_context
            if not av_news_used and news_context:
                self._analyze_news_keywords(news_context, result)

            # 2. Analyst consensus and price targets (FMP via OpenBB)
            try:
                from src.us_stock_modules.openbb_utils import (
                    obb_analyst_consensus,
                    obb_price_historical,
                )

                consensus = obb_analyst_consensus(code)
                if consensus:
                    # 2a. Analyst ratings (from AV sentiment distribution)
                    strong_buy = int(consensus.get("strong_buy_ratings") or 0)
                    buy = int(consensus.get("buy_ratings") or 0)
                    hold = int(consensus.get("hold_ratings") or 0)
                    sell = int(consensus.get("sell_ratings") or 0)
                    strong_sell = int(consensus.get("strong_sell_ratings") or 0)

                    result.analyst_buy = strong_buy + buy
                    result.analyst_hold = hold
                    result.analyst_sell = sell + strong_sell
                    result.analyst_total = result.analyst_buy + result.analyst_hold + result.analyst_sell

                    if result.analyst_total > 0:
                        buy_pct = result.analyst_buy / result.analyst_total
                        sell_pct = result.analyst_sell / result.analyst_total
                        if buy_pct >= 0.7:
                            result.analyst_consensus = "strong_buy"
                        elif buy_pct >= 0.5:
                            result.analyst_consensus = "buy"
                        elif sell_pct >= 0.7:
                            result.analyst_consensus = "strong_sell"
                        elif sell_pct >= 0.5:
                            result.analyst_consensus = "sell"
                        else:
                            result.analyst_consensus = "hold"

                    # 2b. Price targets (FMP consensus)
                    result.target_mean = self._safe_float(consensus.get("consensus_price_target"))
                    result.target_high = self._safe_float(consensus.get("high_price_target"))
                    result.target_low = self._safe_float(consensus.get("low_price_target"))
                    result.num_analysts = consensus.get("num_analysts") or result.analyst_total

                    # Current price for upside calculation
                    if result.target_mean is not None:
                        hist = obb_price_historical(code, period="5d")
                        if hist is not None and len(hist) > 0:
                            current_price = float(hist["Close"].iloc[-1])
                            if current_price > 0:
                                result.target_upside_pct = (
                                    (result.target_mean - current_price) / current_price
                                ) * 100

            except Exception as e:
                logger.debug(f"[{code}] Could not fetch analyst data from OpenBB: {e}")

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

    def _analyze_news_keywords(self, news_context: str, result: SentimentResult) -> None:
        """Fallback: keyword-based news sentiment when AV is unavailable."""
        try:
            text_lower = news_context.lower()
            positive_kw = [
                "beat", "exceeded", "upgrade", "outperform", "bullish", "rally",
                "surge", "record", "strong", "growth", "buyback", "optimistic",
            ]
            negative_kw = [
                "miss", "downgrade", "underperform", "bearish", "decline", "drop",
                "loss", "weak", "warning", "layoff", "lawsuit", "bankruptcy",
            ]

            for keyword in positive_kw:
                result.news_positive_count += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
            for keyword in negative_kw:
                result.news_negative_count += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))

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
            logger.debug(f"Keyword news analysis failed: {e}")
            result.news_sentiment = "neutral"

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Safely convert a value to float."""
        if value is None:
            return None
        try:
            v = float(value)
            if v != v:  # NaN check
                return None
            return v
        except (TypeError, ValueError):
            return None

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
