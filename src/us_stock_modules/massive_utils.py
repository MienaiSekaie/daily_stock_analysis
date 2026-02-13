# -*- coding: utf-8 -*-
"""
DEPRECATED: Use openbb_utils.py instead.

This module is retained for backward compatibility. All new code should
use functions from openbb_utils.py (e.g. obb_price_historical, obb_financial_ratios).
"""

import warnings
warnings.warn(
    "massive_utils is deprecated, use openbb_utils instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

import logging
import os
import threading
import time
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global rate limiter (RPM=5 → 12 seconds between calls)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_last_call_time: float = 0.0
_MIN_INTERVAL: float = 12.0  # 60 / 5 RPM = 12 seconds

# ---------------------------------------------------------------------------
# In-memory cache (shared across all modules within one process)
# ---------------------------------------------------------------------------
_download_cache: dict = {}  # key -> (timestamp, DataFrame)
_cache_lock = threading.Lock()
_DEFAULT_CACHE_TTL = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Lazy-initialized RESTClient singleton
# ---------------------------------------------------------------------------
_client = None
_client_lock = threading.Lock()


def _get_client():
    """Get or create the Massive RESTClient singleton."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                from massive import RESTClient

                api_key = os.getenv("MASSIVE_API_KEY")
                if not api_key:
                    raise ValueError(
                        "MASSIVE_API_KEY environment variable is not set. "
                        "Please set it in your .env file."
                    )
                _client = RESTClient(api_key=api_key, retries=3)
                logger.info("[massive_utils] RESTClient initialized")
    return _client


def _throttle():
    """Enforce minimum interval between Massive API calls (RPM=5)."""
    global _last_call_time
    with _lock:
        now = time.time()
        elapsed = now - _last_call_time
        if elapsed < _MIN_INTERVAL:
            wait = _MIN_INTERVAL - elapsed
            logger.debug(f"[massive_utils] Throttling {wait:.1f}s (RPM=5)")
            time.sleep(wait)
        _last_call_time = time.time()


def _cache_key(ticker: str, **kwargs) -> str:
    """Build a hashable cache key from download arguments."""
    parts = [ticker]
    for k in sorted(kwargs.keys()):
        parts.append(f"{k}={kwargs[k]}")
    return "|".join(parts)


def _period_to_dates(period: str) -> tuple:
    """
    Convert yfinance-style period string to (from_date, to_date) strings.

    Adds extra margin for weekends/holidays so we always get enough trading days.
    """
    period_map = {
        "5d": timedelta(days=10),
        "10d": timedelta(days=18),
        "1mo": timedelta(days=35),
        "2mo": timedelta(days=65),
        "3mo": timedelta(days=95),
        "4mo": timedelta(days=125),
        "6mo": timedelta(days=185),
        "1y": timedelta(days=370),
    }

    delta = period_map.get(period)
    if delta is None:
        # Try to parse numeric days: "20d" -> 20 days
        if period.endswith("d") and period[:-1].isdigit():
            days = int(period[:-1])
            delta = timedelta(days=int(days * 1.8) + 2)
        elif period.endswith("mo") and period[:-2].isdigit():
            months = int(period[:-2])
            delta = timedelta(days=months * 32)
        else:
            delta = timedelta(days=125)  # default ~4 months
            logger.warning(f"[massive_utils] Unknown period '{period}', using 4mo default")

    to_date = date.today()
    from_date = to_date - delta
    return from_date.isoformat(), to_date.isoformat()


def _aggs_to_dataframe(aggs: list) -> pd.DataFrame:
    """
    Convert a list of Massive Agg objects to a pandas DataFrame
    matching yfinance output format.

    Returns DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume
    """
    if not aggs:
        return pd.DataFrame()

    rows = []
    for agg in aggs:
        ts = getattr(agg, "timestamp", None)
        if ts is None:
            continue
        # timestamp is in milliseconds
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000)
        else:
            dt = ts

        rows.append(
            {
                "Date": dt,
                "Open": getattr(agg, "open", None),
                "High": getattr(agg, "high", None),
                "Low": getattr(agg, "low", None),
                "Close": getattr(agg, "close", None),
                "Volume": getattr(agg, "volume", None),
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")
    df = df.sort_index()
    return df


def clear_cache():
    """Clear all cached data (useful between sessions)."""
    global _download_cache
    with _cache_lock:
        _download_cache.clear()
    logger.debug("[massive_utils] Cache cleared")


# ---------------------------------------------------------------------------
# massive_download — rate-limited, cached, with retry
# ---------------------------------------------------------------------------
def massive_download(
    ticker: str,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_retries: int = 3,
    cache_ttl: int = _DEFAULT_CACHE_TTL,
) -> pd.DataFrame:
    """
    Rate-limited wrapper around Massive RESTClient.get_aggs() with cache and retry.

    Returns a DataFrame with the same format as yfinance:
    - DatetimeIndex
    - Columns: Open, High, Low, Close, Volume

    Args:
        ticker: US stock ticker (e.g. "AAPL", "SPY")
        period: yfinance-style period string (e.g. "10d", "4mo"). Used if start/end not set.
        start: Start date string (YYYY-MM-DD)
        end: End date string (YYYY-MM-DD)
        max_retries: Number of retry attempts
        cache_ttl: Cache duration in seconds (0 to disable)

    Returns:
        DataFrame with OHLCV data, or empty DataFrame on failure
    """
    # Determine date range
    if start and end:
        from_date, to_date = start, end
    elif period:
        from_date, to_date = _period_to_dates(period)
    else:
        from_date, to_date = _period_to_dates("4mo")

    # Check cache
    key = _cache_key(ticker, from_date=from_date, to_date=to_date)
    if cache_ttl > 0:
        with _cache_lock:
            if key in _download_cache:
                cached_time, cached_df = _download_cache[key]
                if time.time() - cached_time < cache_ttl:
                    logger.debug(f"[massive_download] Cache hit: '{ticker}'")
                    return cached_df.copy()

    for attempt in range(max_retries):
        _throttle()
        try:
            client = _get_client()
            aggs = client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=from_date,
                to=to_date,
                adjusted=True,
                limit=50000,
            )

            df = _aggs_to_dataframe(aggs)

            if df is not None and len(df) > 0:
                # Cache successful result
                if cache_ttl > 0:
                    with _cache_lock:
                        _download_cache[key] = (time.time(), df.copy())
                logger.debug(f"[massive_download] '{ticker}' fetched {len(df)} bars")
                return df

            # Empty result — retry with backoff
            if attempt < max_retries - 1:
                wait = 2**attempt * 3  # 3s, 6s, 12s
                logger.debug(
                    f"[massive_download] Empty result for '{ticker}', "
                    f"retry {attempt + 1}/{max_retries} after {wait}s"
                )
                time.sleep(wait)
                continue

            logger.warning(f"[massive_download] '{ticker}' returned no data after {max_retries} attempts")
            return pd.DataFrame()

        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "429" in err_str or "too many" in err_str:
                wait = 2**attempt * 5  # 5s, 10s, 20s
                logger.debug(
                    f"[massive_download] Rate limited on '{ticker}', "
                    f"retry {attempt + 1}/{max_retries} after {wait}s"
                )
                time.sleep(wait)
            elif attempt < max_retries - 1:
                wait = 2**attempt * 3
                logger.debug(
                    f"[massive_download] '{ticker}' failed: {e}, "
                    f"retry {attempt + 1}/{max_retries} after {wait}s"
                )
                time.sleep(wait)
            else:
                logger.warning(f"[massive_download] '{ticker}' failed: {e}")
                return pd.DataFrame()

    logger.warning(f"[massive_download] '{ticker}' failed after {max_retries} retries")
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# massive_financials_ratios — rate-limited, cached
# ---------------------------------------------------------------------------
def massive_financials_ratios(ticker: str, cache_ttl: int = _DEFAULT_CACHE_TTL) -> dict:
    """
    Fetch financial ratios for a ticker via Massive API.

    Returns dict with keys matching the Massive FinancialRatio model:
    price_to_earnings, price_to_book, price_to_sales, return_on_equity,
    return_on_assets, debt_to_equity, current, quick, free_cash_flow,
    dividend_yield, market_cap, earnings_per_share, etc.
    Returns empty dict on failure.
    """
    key = _cache_key(ticker, endpoint="ratios")
    if cache_ttl > 0:
        with _cache_lock:
            if key in _download_cache:
                cached_time, cached_data = _download_cache[key]
                if time.time() - cached_time < cache_ttl:
                    logger.debug(f"[massive_financials_ratios] Cache hit: '{ticker}'")
                    return cached_data.copy()

    _throttle()
    try:
        client = _get_client()
        ratios_list = list(client.list_financials_ratios(ticker=ticker, limit=1))
        if ratios_list:
            ratio = ratios_list[0]
            data = {k: v for k, v in ratio.__dict__.items() if not k.startswith("_")}
            if cache_ttl > 0:
                with _cache_lock:
                    _download_cache[key] = (time.time(), data.copy())
            logger.debug(f"[massive_financials_ratios] '{ticker}' fetched successfully")
            return data
    except Exception as e:
        logger.debug(f"[massive_financials_ratios] '{ticker}' failed: {e}")

    return {}


# ---------------------------------------------------------------------------
# massive_income_statements — rate-limited, cached
# ---------------------------------------------------------------------------
def massive_income_statements(ticker: str, limit: int = 2, cache_ttl: int = _DEFAULT_CACHE_TTL) -> list:
    """
    Fetch income statement data for a ticker via Massive API.

    Returns list of dicts (most recent first), each with keys like:
    revenue, cost_of_revenue, gross_profit, operating_income,
    consolidated_net_income_loss, basic_earnings_per_share, etc.
    Returns empty list on failure.
    """
    key = _cache_key(ticker, endpoint="income", limit=limit)
    if cache_ttl > 0:
        with _cache_lock:
            if key in _download_cache:
                cached_time, cached_data = _download_cache[key]
                if time.time() - cached_time < cache_ttl:
                    logger.debug(f"[massive_income_statements] Cache hit: '{ticker}'")
                    return [d.copy() for d in cached_data]

    _throttle()
    try:
        client = _get_client()
        stmts = list(client.list_financials_income_statements(ticker=ticker, limit=limit))
        if stmts:
            data = [{k: v for k, v in s.__dict__.items() if not k.startswith("_")} for s in stmts]
            if cache_ttl > 0:
                with _cache_lock:
                    _download_cache[key] = (time.time(), [d.copy() for d in data])
            logger.debug(f"[massive_income_statements] '{ticker}' fetched {len(data)} statements")
            return data
    except Exception as e:
        logger.debug(f"[massive_income_statements] '{ticker}' failed: {e}")

    return []


# ---------------------------------------------------------------------------
# massive_benzinga_consensus — rate-limited, cached
# ---------------------------------------------------------------------------
def massive_benzinga_consensus(ticker: str, cache_ttl: int = _DEFAULT_CACHE_TTL) -> dict:
    """
    Fetch Benzinga analyst consensus ratings for a ticker.

    Returns dict with keys: consensus_rating, buy_ratings, hold_ratings,
    sell_ratings, strong_buy_ratings, strong_sell_ratings,
    consensus_price_target, high_price_target, low_price_target, etc.
    Returns empty dict on failure.
    """
    key = _cache_key(ticker, endpoint="benzinga_consensus")
    if cache_ttl > 0:
        with _cache_lock:
            if key in _download_cache:
                cached_time, cached_data = _download_cache[key]
                if time.time() - cached_time < cache_ttl:
                    logger.debug(f"[massive_benzinga_consensus] Cache hit: '{ticker}'")
                    return cached_data.copy()

    _throttle()
    try:
        client = _get_client()
        results = list(client.list_benzinga_consensus_ratings(ticker=ticker))
        if results:
            data = {k: v for k, v in results[0].__dict__.items() if not k.startswith("_")}
            if cache_ttl > 0:
                with _cache_lock:
                    _download_cache[key] = (time.time(), data.copy())
            logger.debug(f"[massive_benzinga_consensus] '{ticker}' fetched successfully")
            return data
    except Exception as e:
        logger.debug(f"[massive_benzinga_consensus] '{ticker}' failed: {e}")

    return {}


# ---------------------------------------------------------------------------
# massive_benzinga_earnings — rate-limited, cached
# ---------------------------------------------------------------------------
def massive_benzinga_earnings(ticker: str, limit: int = 4, cache_ttl: int = _DEFAULT_CACHE_TTL) -> list:
    """
    Fetch Benzinga earnings data for a ticker.

    Returns list of dicts with keys: date, fiscal_year, fiscal_period,
    estimated_eps, actual_eps, eps_surprise_percent,
    estimated_revenue, actual_revenue, date_status, etc.
    Returns empty list on failure.
    """
    key = _cache_key(ticker, endpoint="benzinga_earnings", limit=limit)
    if cache_ttl > 0:
        with _cache_lock:
            if key in _download_cache:
                cached_time, cached_data = _download_cache[key]
                if time.time() - cached_time < cache_ttl:
                    logger.debug(f"[massive_benzinga_earnings] Cache hit: '{ticker}'")
                    return [d.copy() for d in cached_data]

    _throttle()
    try:
        client = _get_client()
        results = list(client.list_benzinga_earnings(ticker=ticker, limit=limit))
        if results:
            data = [{k: v for k, v in e.__dict__.items() if not k.startswith("_")} for e in results]
            if cache_ttl > 0:
                with _cache_lock:
                    _download_cache[key] = (time.time(), [d.copy() for d in data])
            logger.debug(f"[massive_benzinga_earnings] '{ticker}' fetched {len(data)} records")
            return data
    except Exception as e:
        logger.debug(f"[massive_benzinga_earnings] '{ticker}' failed: {e}")

    return []
