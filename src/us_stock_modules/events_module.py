# -*- coding: utf-8 -*-
"""
Module 5: Event Calendar & Catalysts

Evaluates upcoming events that could impact the stock:
- Next earnings date
- FOMC meetings
- Monthly options expiration (OPEX)
- Historical Volatility

Data sources:
- Earnings dates: OpenBB SDK (Nasdaq/FMP calendar)
- FOMC/OPEX: hardcoded calendar (fomc_calendar.py)
- HV: computed from daily returns via OpenBB K-line data (20-day)
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EventItem:
    """A single upcoming event."""
    date: str  # ISO date string
    event: str  # Event name
    impact: str  # Brief impact description
    days_away: int = 0


@dataclass
class EventsResult:
    """Event calendar analysis result."""

    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)

    next_earnings: Optional[str] = None  # ISO date
    earnings_days_away: Optional[int] = None

    next_fomc: Optional[str] = None
    fomc_days_away: Optional[int] = None

    next_opex: Optional[str] = None
    opex_days_away: Optional[int] = None

    iv: Optional[float] = None  # Implied volatility as percentage
    hv: Optional[float] = None  # Historical volatility as percentage
    iv_hv_signal: str = ""  # "iv_premium" / "iv_discount" / "neutral"

    score: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "upcoming_events": self.upcoming_events,
            "next_earnings": self.next_earnings,
            "earnings_days_away": self.earnings_days_away,
            "next_fomc": self.next_fomc,
            "fomc_days_away": self.fomc_days_away,
            "next_opex": self.next_opex,
            "opex_days_away": self.opex_days_away,
            "iv": round(self.iv, 2) if self.iv is not None else None,
            "hv": round(self.hv, 2) if self.hv is not None else None,
            "iv_hv_signal": self.iv_hv_signal,
            "score": self.score,
        }


class EventsModule:
    """Event calendar and catalysts analyzer."""

    def analyze(self, code: str) -> Optional[EventsResult]:
        """
        Analyze upcoming events and volatility metrics.

        Args:
            code: US stock ticker

        Returns:
            EventsResult or None
        """
        try:
            result = EventsResult()
            today = date.today()

            # 1. FOMC and OPEX dates (no API call needed)
            from src.us_stock_modules.fomc_calendar import (
                get_next_fomc,
                get_next_opex,
                get_upcoming_fomc,
                days_until,
            )

            next_fomc = get_next_fomc(today)
            if next_fomc:
                result.next_fomc = next_fomc.isoformat()
                result.fomc_days_away = days_until(next_fomc, today)
                if result.fomc_days_away <= 30:
                    result.upcoming_events.append({
                        "date": result.next_fomc,
                        "event": "FOMC Meeting",
                        "impact": f"Rate decision in {result.fomc_days_away} days — potential volatility for all equities",
                        "days_away": result.fomc_days_away,
                    })

            next_opex = get_next_opex(today)
            result.next_opex = next_opex.isoformat()
            result.opex_days_away = days_until(next_opex, today)
            if result.opex_days_away <= 14:
                result.upcoming_events.append({
                    "date": result.next_opex,
                    "event": "Monthly OPEX",
                    "impact": f"Options expiration in {result.opex_days_away} days — gamma effects may amplify moves",
                    "days_away": result.opex_days_away,
                })

            # 2. Earnings date (OpenBB earnings calendar)
            try:
                from src.us_stock_modules.openbb_utils import obb_earnings_calendar

                earnings = obb_earnings_calendar(code, limit=4)
                if earnings:
                    for earn in earnings:
                        earn_date_str = earn.get("date")
                        if not earn_date_str:
                            continue
                        try:
                            earn_date = date.fromisoformat(earn_date_str[:10])
                        except (ValueError, TypeError):
                            continue

                        if earn_date >= today:
                            result.next_earnings = earn_date.isoformat()
                            result.earnings_days_away = days_until(earn_date, today)
                            if result.earnings_days_away <= 45:
                                result.upcoming_events.append({
                                    "date": result.next_earnings,
                                    "event": f"{code} Earnings Report",
                                    "impact": (
                                        f"Earnings in {result.earnings_days_away} days — "
                                        f"{'HIGH RISK: position with caution' if result.earnings_days_away <= 14 else 'monitor for pre-earnings run'}"
                                    ),
                                    "days_away": result.earnings_days_away,
                                })
                            break  # Found the next future earnings date

            except Exception as e:
                logger.debug(f"[{code}] Could not fetch earnings dates from OpenBB: {e}")

            # 3. Historical Volatility (from Massive K-line data — avoids yfinance for price data)
            self._calculate_hv(code, result)

            # IV vs HV signal
            if result.iv is not None and result.hv is not None and result.hv > 0:
                ratio = result.iv / result.hv
                if ratio > 1.2:
                    result.iv_hv_signal = "iv_premium"
                elif ratio < 0.8:
                    result.iv_hv_signal = "iv_discount"
                else:
                    result.iv_hv_signal = "neutral"

            # Sort events by date
            result.upcoming_events.sort(key=lambda x: x.get("days_away", 999))

            # Score
            self._calculate_score(result)

            logger.info(
                f"[{code}] Events: {len(result.upcoming_events)} upcoming, "
                f"IV={result.iv}, HV={result.hv}, score={result.score}"
            )
            return result

        except Exception as e:
            logger.warning(f"[{code}] Events analysis failed: {e}")
            return None

    def _calculate_hv(self, code: str, result: EventsResult) -> None:
        """Calculate historical volatility from OpenBB K-line data."""
        try:
            from src.us_stock_modules.openbb_utils import obb_price_historical

            hist = obb_price_historical(code, period="2mo")
            if hist is not None and len(hist) >= 21:
                returns = hist["Close"].pct_change().dropna()
                if len(returns) >= 20:
                    hv_daily = float(returns.tail(20).std())
                    result.hv = hv_daily * math.sqrt(252) * 100  # Annualized %

        except ImportError:
            logger.debug("openbb not installed, skipping HV calculation")
        except Exception as e:
            logger.debug(f"[{code}] HV calculation failed: {e}")

    def _calculate_score(self, result: EventsResult) -> None:
        """
        Calculate events score (0-100).

        Higher score = fewer imminent risks / events well-positioned.
        Lower score = earnings imminent / high IV premium / multiple events.
        """
        score = 70  # Start neutral-positive (no events = good)

        # Earnings proximity penalty
        if result.earnings_days_away is not None:
            if result.earnings_days_away <= 7:
                score -= 25  # Very close, high uncertainty
            elif result.earnings_days_away <= 14:
                score -= 15
            elif result.earnings_days_away <= 30:
                score -= 5

        # FOMC proximity penalty
        if result.fomc_days_away is not None and result.fomc_days_away <= 7:
            score -= 10

        # IV premium penalty (market expects big move)
        if result.iv_hv_signal == "iv_premium":
            score -= 10
        elif result.iv_hv_signal == "iv_discount":
            score += 5  # Options cheap, good for entry

        # Multiple events stacking = more uncertainty
        if len(result.upcoming_events) >= 3:
            score -= 5

        result.score = min(100, max(0, score))
