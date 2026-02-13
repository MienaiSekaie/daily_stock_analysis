# -*- coding: utf-8 -*-
"""
OpenBB SDK data fetcher for US stocks.

Uses OpenBB SDK to fetch daily OHLCV data for US stock tickers.
Non-US stocks (A-shares, HK) are rejected so the DataFetcherManager
falls through to other fetchers (efinance, akshare, etc.).
"""

import logging
import os
import re
from typing import Optional

import pandas as pd

from data_provider.base import BaseFetcher, DataFetchError
from data_provider.realtime_types import UnifiedRealtimeQuote, RealtimeSource

logger = logging.getLogger(__name__)


class OpenBBFetcher(BaseFetcher):
    """
    OpenBB SDK data source for US stocks.

    Priority is configurable via OPENBB_PRIORITY env var (default: 3).
    Only handles US stock codes (1-5 uppercase letters, optional .X suffix).
    """

    name = "OpenBBFetcher"
    priority = int(os.getenv("OPENBB_PRIORITY", "3"))

    _US_STOCK_RE = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")

    def _is_us_stock(self, stock_code: str) -> bool:
        """Check if code is a US stock ticker."""
        return bool(self._US_STOCK_RE.match(stock_code.strip().upper()))

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch US stock OHLCV data via OpenBB SDK.

        Raises DataFetchError for non-US stocks so the manager tries the next fetcher.
        """
        if not self._is_us_stock(stock_code):
            raise DataFetchError(f"[OpenBBFetcher] '{stock_code}' is not a US stock, skipping")

        from src.us_stock_modules.openbb_utils import obb_price_historical

        ticker = stock_code.strip().upper()
        logger.debug(f"[OpenBBFetcher] Fetching {ticker} ({start_date} ~ {end_date})")

        df = obb_price_historical(ticker, start=start_date, end=end_date)

        if df is None or df.empty:
            raise DataFetchError(f"[OpenBBFetcher] No data returned for {ticker}")

        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        Normalize OpenBB output to standard columns.

        Input: DataFrame with DatetimeIndex and columns Open, High, Low, Close, Volume
        Output: DataFrame with standard columns: date, open, high, low, close, volume, amount, pct_chg
        """
        result = pd.DataFrame()

        # Map columns (OpenBB returns capitalized via openbb_utils wrapper)
        col_map = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        for src, dst in col_map.items():
            if src in df.columns:
                result[dst] = df[src]

        # Date from index
        if df.index.name in ("Date", "date") or isinstance(df.index, pd.DatetimeIndex):
            result["date"] = pd.to_datetime(df.index).strftime("%Y-%m-%d")
        else:
            result["date"] = df.index.astype(str)

        # Calculate derived fields
        if "close" in result.columns:
            result["pct_chg"] = result["close"].pct_change() * 100

        if "volume" in result.columns and "close" in result.columns:
            result["amount"] = result["volume"] * result["close"]
        else:
            result["amount"] = 0.0

        result = result.reset_index(drop=True)
        return result

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        Get realtime quote via OpenBB for US stocks.

        Uses FMP provider for quote data.
        Returns None for non-US stocks.
        """
        if not self._is_us_stock(stock_code):
            return None

        try:
            from src.us_stock_modules.openbb_utils import _get_obb

            obb = _get_obb()
            result = obb.equity.price.quote(symbol=stock_code.upper(), provider="fmp")
            df = result.to_df()

            if df is None or df.empty:
                return None

            row = df.iloc[0].to_dict()

            quote = UnifiedRealtimeQuote(
                code=stock_code.upper(),
                name=row.get("name", ""),
                source=RealtimeSource.FALLBACK,
                price=row.get("last_price"),
                change_pct=row.get("change_percent", 0) * 100 if row.get("change_percent") else None,
                change_amount=row.get("change"),
                volume=int(row["volume"]) if row.get("volume") else None,
                open_price=row.get("open"),
                high=row.get("high"),
                low=row.get("low"),
                pre_close=row.get("prev_close"),
                total_mv=row.get("market_cap"),
            )
            return quote

        except Exception as e:
            logger.debug(f"[OpenBBFetcher] Realtime quote for {stock_code} failed: {e}")
            return None
