# -*- coding: utf-8 -*-
"""
Module 2: Sector Context

Evaluates a stock's sector positioning:
- Sector ETF vs SPY relative strength (5-day)
- Stock rank within sector peers
- Stock vs sector ETF comparison

K-line data sourced from OpenBB SDK.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SectorResult:
    """Sector context analysis result."""

    etf: str = ""
    sector_name: str = ""
    sub_sector: str = ""

    etf_5d_return: Optional[float] = None  # percentage
    spy_5d_return: Optional[float] = None  # percentage
    stock_5d_return: Optional[float] = None  # percentage

    relative_strength: str = "unknown"  # "outperforming" / "inline" / "underperforming"
    relative_strength_ratio: float = 0.0  # etf_return / spy_return

    stock_rank: str = ""  # e.g. "3/15"
    stock_rank_position: str = ""  # "leader" / "above_avg" / "average" / "laggard"
    peer_returns: Dict[str, float] = None  # {ticker: 5d_return}

    score: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "etf": self.etf,
            "sector_name": self.sector_name,
            "sub_sector": self.sub_sector,
            "etf_5d_return": round(self.etf_5d_return, 2) if self.etf_5d_return is not None else None,
            "spy_5d_return": round(self.spy_5d_return, 2) if self.spy_5d_return is not None else None,
            "stock_5d_return": round(self.stock_5d_return, 2) if self.stock_5d_return is not None else None,
            "relative_strength": self.relative_strength,
            "relative_strength_ratio": round(self.relative_strength_ratio, 2),
            "stock_rank": self.stock_rank,
            "stock_rank_position": self.stock_rank_position,
            "peer_returns": (
                {k: round(v, 2) for k, v in self.peer_returns.items()} if self.peer_returns else None
            ),
            "score": self.score,
        }


class SectorModule:
    """Sector context analyzer using OpenBB SDK."""

    def analyze(self, code: str) -> Optional[SectorResult]:
        """
        Analyze sector positioning for a US stock.

        Args:
            code: US stock ticker (e.g. "AMD")

        Returns:
            SectorResult or None
        """
        try:
            from src.us_stock_modules.openbb_utils import obb_price_historical
            from src.us_stock_modules.sector_mapping import get_sector_info, get_sector_peers

            sector_info = get_sector_info(code)
            etf = sector_info["etf"]
            result = SectorResult(
                etf=etf,
                sector_name=sector_info.get("sector", ""),
                sub_sector=sector_info.get("sub_sector", ""),
            )

            # Fetch 5-day returns for SPY, sector ETF, and the stock
            peers = get_sector_peers(etf)
            # Add peers (excluding the stock itself and limiting to 5 to reduce API calls)
            peer_tickers = [p for p in peers if p != code][:5]
            all_tickers = list(dict.fromkeys([code, etf, "SPY"] + peer_tickers))

            # Download individually (cached) to reduce API calls
            returns = {}
            for ticker in all_tickers:
                try:
                    ticker_data = obb_price_historical(ticker, period="10d")
                    if ticker_data is not None and len(ticker_data) >= 2:
                        closes = ticker_data["Close"].dropna()
                        if len(closes) >= 2:
                            end_price = float(closes.iloc[-1])
                            start_idx = max(0, len(closes) - 6)
                            start_price = float(closes.iloc[start_idx])
                            if start_price > 0:
                                returns[ticker] = (end_price - start_price) / start_price * 100
                except Exception:
                    continue

            if not returns:
                logger.warning(f"[{code}] No sector data available")
                return result

            # Fill in results
            result.stock_5d_return = returns.get(code)
            result.etf_5d_return = returns.get(etf)
            result.spy_5d_return = returns.get("SPY")

            # Relative strength: sector ETF vs SPY
            if result.etf_5d_return is not None and result.spy_5d_return is not None:
                diff = result.etf_5d_return - result.spy_5d_return
                if result.spy_5d_return != 0:
                    result.relative_strength_ratio = result.etf_5d_return / abs(result.spy_5d_return)

                if diff > 1.0:
                    result.relative_strength = "outperforming"
                elif diff > -1.0:
                    result.relative_strength = "inline"
                else:
                    result.relative_strength = "underperforming"

            # Peer ranking
            peer_returns = {t: returns[t] for t in peer_tickers if t in returns}
            if code in returns:
                peer_returns[code] = returns[code]
            result.peer_returns = peer_returns

            if code in returns and len(peer_returns) > 1:
                sorted_peers = sorted(peer_returns.items(), key=lambda x: x[1], reverse=True)
                rank = next((i + 1 for i, (t, _) in enumerate(sorted_peers) if t == code), None)
                total = len(sorted_peers)
                if rank:
                    result.stock_rank = f"{rank}/{total}"
                    percentile = rank / total
                    if percentile <= 0.25:
                        result.stock_rank_position = "leader"
                    elif percentile <= 0.50:
                        result.stock_rank_position = "above_avg"
                    elif percentile <= 0.75:
                        result.stock_rank_position = "average"
                    else:
                        result.stock_rank_position = "laggard"

            # Score
            self._calculate_score(result)

            logger.info(
                f"[{code}] Sector: {etf} {result.relative_strength}, "
                f"rank={result.stock_rank}, score={result.score}"
            )
            return result

        except ImportError:
            logger.error("openbb not installed, cannot run sector analysis")
            return None
        except Exception as e:
            logger.warning(f"[{code}] Sector analysis failed: {e}")
            return None

    def _calculate_score(self, result: SectorResult) -> None:
        """Calculate sector context score (0-100)."""
        score = 50

        # Sector vs SPY (40% weight)
        if result.relative_strength == "outperforming":
            score += 20
        elif result.relative_strength == "inline":
            score += 5
        elif result.relative_strength == "underperforming":
            score -= 15

        # Stock rank in sector (40% weight)
        if result.stock_rank_position == "leader":
            score += 20
        elif result.stock_rank_position == "above_avg":
            score += 10
        elif result.stock_rank_position == "average":
            score += 0
        elif result.stock_rank_position == "laggard":
            score -= 10

        # Sector momentum (20% weight)
        if result.etf_5d_return is not None:
            if result.etf_5d_return > 3:
                score += 10
            elif result.etf_5d_return > 1:
                score += 5
            elif result.etf_5d_return < -3:
                score -= 10
            elif result.etf_5d_return < -1:
                score -= 5

        result.score = min(100, max(0, score))
