# -*- coding: utf-8 -*-
"""
Shared OpenBB SDK utilities for US stock modules.

Replaces massive_utils.py (Polygon.io) and fred_utils.py (fredapi) with
unified OpenBB SDK wrappers. Provides:
- Thread-safe in-memory cache with configurable TTL
- Retry with exponential backoff on transient errors
- DataFrame output matching yfinance format (capitalized columns, DatetimeIndex)
- Graceful degradation: returns None/empty on failure
"""

import logging
import os
import threading
import time
from datetime import date, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache (shared across all modules within one process)
# ---------------------------------------------------------------------------
_cache: dict = {}  # key -> (timestamp, data)
_cache_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Global rate limiter for Polygon provider (RPM=5 → min 12s between calls)
# Other providers (FMP, FRED) have much higher limits and skip throttling.
# ---------------------------------------------------------------------------
_price_lock = threading.Lock()
_last_price_call: float = 0.0
_POLYGON_MIN_INTERVAL: float = 12.0  # 60 / 5 RPM


def _throttle_polygon():
    """Enforce minimum interval between Polygon API calls."""
    global _last_price_call
    with _price_lock:
        now = time.time()
        elapsed = now - _last_price_call
        if elapsed < _POLYGON_MIN_INTERVAL:
            wait = _POLYGON_MIN_INTERVAL - elapsed
            logger.debug(f"[openbb_utils] Throttling Polygon {wait:.1f}s")
            time.sleep(wait)
        _last_price_call = time.time()


def _get_cache_ttl() -> int:
    """Get cache TTL from config, with fallback default."""
    try:
        from src.config import get_config
        return getattr(get_config(), "openbb_cache_ttl", 3600)
    except Exception:
        return 3600


def _get_provider(data_type: str) -> str:
    """Get preferred provider for a data type from config."""
    try:
        from src.config import get_config
        cfg = get_config()
        mapping = {
            "price": getattr(cfg, "openbb_price_provider", "polygon"),
            "fundamental": getattr(cfg, "openbb_fundamental_provider", "fmp"),
            "earnings": getattr(cfg, "openbb_earnings_provider", "fmp"),
            "macro": getattr(cfg, "openbb_macro_provider", "fred"),
        }
        return mapping.get(data_type, "fmp")
    except Exception:
        defaults = {"price": "polygon", "fundamental": "fmp", "earnings": "fmp", "macro": "fred"}
        return defaults.get(data_type, "fmp")


def _cache_key(endpoint: str, **kwargs) -> str:
    """Build a hashable cache key from endpoint and arguments."""
    parts = [endpoint]
    for k in sorted(kwargs.keys()):
        parts.append(f"{k}={kwargs[k]}")
    return "|".join(parts)


def _cache_get(key: str, cache_ttl: Optional[int] = None):
    """Get value from cache if still valid. Returns None if expired or missing."""
    ttl = cache_ttl if cache_ttl is not None else _get_cache_ttl()
    if ttl <= 0:
        return None
    with _cache_lock:
        if key in _cache:
            cached_time, cached_data = _cache[key]
            if time.time() - cached_time < ttl:
                return cached_data
    return None


def _cache_set(key: str, data):
    """Store value in cache with current timestamp."""
    with _cache_lock:
        _cache[key] = (time.time(), data)


def clear_cache():
    """Clear all cached data (useful between sessions)."""
    global _cache
    with _cache_lock:
        _cache.clear()
    logger.debug("[openbb_utils] Cache cleared")


# ---------------------------------------------------------------------------
# Lazy-initialized OBB singleton
# ---------------------------------------------------------------------------
_obb = None
_obb_lock = threading.Lock()


def _get_obb():
    """Get or create the OpenBB obb singleton."""
    global _obb
    if _obb is None:
        with _obb_lock:
            if _obb is None:
                from openbb import obb
                _obb = obb
                logger.info("[openbb_utils] OpenBB SDK initialized")
    return _obb


# ---------------------------------------------------------------------------
# Alpha Vantage direct API helpers (replaces yfinance for earnings + sentiment)
# ---------------------------------------------------------------------------
_AV_BASE_URL = "https://www.alphavantage.co/query"


def _get_av_api_key() -> Optional[str]:
    """Get Alpha Vantage API key from .env or OBB credentials."""
    key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if key:
        return key
    try:
        obb = _get_obb()
        return str(obb.user.credentials.alpha_vantage_api_key)
    except Exception:
        return None


def _av_request(params: dict, label: str = "") -> Optional[dict]:
    """Make a cached, retried request to Alpha Vantage API."""
    api_key = _get_av_api_key()
    if not api_key:
        logger.debug(f"[av] No Alpha Vantage API key, skipping {label}")
        return None
    params["apikey"] = api_key
    for attempt in range(2):
        try:
            resp = requests.get(_AV_BASE_URL, params=params, timeout=15)
            data = resp.json()
            if "Information" in data and "rate" in data["Information"].lower():
                if attempt == 0:
                    logger.debug(f"[av] {label} rate limited, retry after 15s")
                    time.sleep(15)
                    continue
            if "Error Message" in data:
                logger.debug(f"[av] {label} error: {data['Error Message']}")
                return None
            return data
        except Exception as e:
            logger.debug(f"[av] {label} request failed: {e}")
            if attempt == 0:
                time.sleep(2)
    return None


def av_news_sentiment(ticker: str, limit: int = 50, cache_ttl: Optional[int] = None) -> dict:
    """
    Fetch news sentiment via Alpha Vantage NEWS_SENTIMENT endpoint.

    Returns dict with:
      - articles: list of {title, url, time_published, sentiment_score, sentiment_label, relevance}
      - avg_sentiment: float (-1 to 1)
      - positive_count, negative_count, neutral_count: int
      - sentiment_label: "positive" / "negative" / "neutral"
    """
    key = _cache_key("av_news_sentiment", ticker=ticker)
    cached = _cache_get(key, cache_ttl)
    if cached is not None:
        return cached

    data = _av_request(
        {"function": "NEWS_SENTIMENT", "tickers": ticker, "limit": str(limit), "sort": "LATEST"},
        label=f"av_news_sentiment({ticker})",
    )
    if not data or "feed" not in data:
        return {}

    articles = []
    sentiment_scores = []
    for article in data["feed"]:
        # Find ticker-specific sentiment
        ticker_sent = None
        for ts in article.get("ticker_sentiment", []):
            if ts.get("ticker", "").upper() == ticker.upper():
                ticker_sent = ts
                break

        score = float(ticker_sent["ticker_sentiment_score"]) if ticker_sent else None
        label = ticker_sent.get("ticker_sentiment_label", "") if ticker_sent else ""
        relevance = float(ticker_sent["relevance_score"]) if ticker_sent else 0

        if score is not None and relevance >= 0.3:
            sentiment_scores.append(score)

        articles.append({
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "time_published": article.get("time_published", ""),
            "sentiment_score": score,
            "sentiment_label": label,
            "relevance": relevance,
        })

    # Aggregate sentiment
    positive_count = sum(1 for s in sentiment_scores if s >= 0.15)
    negative_count = sum(1 for s in sentiment_scores if s <= -0.15)
    neutral_count = sum(1 for s in sentiment_scores if -0.15 < s < 0.15)
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

    if avg_sentiment >= 0.15:
        overall_label = "positive"
    elif avg_sentiment <= -0.15:
        overall_label = "negative"
    else:
        overall_label = "neutral"

    result = {
        "articles": articles,
        "avg_sentiment": round(avg_sentiment, 4),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "sentiment_label": overall_label,
        "total_scored": len(sentiment_scores),
    }

    _cache_set(key, result)
    logger.debug(
        f"[av_news_sentiment] '{ticker}' {len(articles)} articles, "
        f"avg={avg_sentiment:.3f} ({overall_label}), +{positive_count}/-{negative_count}"
    )
    return result


def _safe_float_val(val) -> Optional[float]:
    """Convert AV string values to float, handling 'None' strings."""
    if val is None or val == "None" or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Period → date range conversion (ported from massive_utils.py)
# ---------------------------------------------------------------------------
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
        if period.endswith("d") and period[:-1].isdigit():
            days = int(period[:-1])
            delta = timedelta(days=int(days * 1.8) + 2)
        elif period.endswith("mo") and period[:-2].isdigit():
            months = int(period[:-2])
            delta = timedelta(days=months * 32)
        else:
            delta = timedelta(days=125)
            logger.warning(f"[openbb_utils] Unknown period '{period}', using 4mo default")

    to_date = date.today()
    from_date = to_date - delta
    return from_date.isoformat(), to_date.isoformat()


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------
def _retry(func, max_retries: int = 3, label: str = ""):
    """Execute func with exponential backoff retry on exceptions."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "rate" in err_str or "429" in err_str or "too many" in err_str
            wait = 2 ** attempt * (5 if is_rate_limit else 2)
            if attempt < max_retries - 1:
                logger.debug(
                    f"[openbb_utils] {label} attempt {attempt + 1}/{max_retries} failed: {e}, "
                    f"retry after {wait}s"
                )
                time.sleep(wait)
            else:
                logger.warning(f"[openbb_utils] {label} failed after {max_retries} attempts: {e}")
                raise
    return None


# ===========================================================================
# Public API: Data fetching functions
# ===========================================================================


def obb_price_historical(
    ticker: str,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    provider: Optional[str] = None,
    cache_ttl: Optional[int] = None,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data via OpenBB.

    Drop-in replacement for massive_download(). Returns DataFrame with
    DatetimeIndex and capitalized columns: Open, High, Low, Close, Volume.

    Args:
        ticker: US stock ticker (e.g. "AAPL", "SPY")
        period: yfinance-style period string (e.g. "10d", "2mo")
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        provider: OBB provider override (default from config)
        cache_ttl: Cache TTL override in seconds

    Returns:
        DataFrame with OHLCV data, or empty DataFrame on failure
    """
    if start and end:
        from_date, to_date = start, end
    elif period:
        from_date, to_date = _period_to_dates(period)
    else:
        from_date, to_date = _period_to_dates("4mo")

    key = _cache_key("price_historical", ticker=ticker, from_date=from_date, to_date=to_date)
    cached = _cache_get(key, cache_ttl)
    if cached is not None:
        logger.debug(f"[obb_price_historical] Cache hit: '{ticker}'")
        return cached.copy()

    # Smart cache: try to extract from a longer cached period for the same ticker
    # This avoids redundant Polygon API calls when 4mo is cached but 5d/10d/2mo is requested
    from_dt = pd.Timestamp(from_date)
    smart_subset = None
    with _cache_lock:
        for ck, (_, cdata) in _cache.items():
            if (
                ck.startswith("price_historical|")
                and f"ticker={ticker}" in ck
                and isinstance(cdata, pd.DataFrame)
                and not cdata.empty
            ):
                if cdata.index.min() <= from_dt:
                    subset = cdata[cdata.index >= from_dt].copy()
                    if len(subset) >= 2:
                        smart_subset = subset
                        break
    # Set cache OUTSIDE the lock to avoid deadlock (_cache_set also acquires _cache_lock)
    if smart_subset is not None:
        logger.debug(f"[obb_price_historical] Smart cache hit: '{ticker}' ({len(smart_subset)} rows from superset)")
        _cache_set(key, smart_subset.copy())
        return smart_subset

    prov = provider or _get_provider("price")

    try:
        def _fetch():
            # Throttle Polygon calls to stay within RPM=5 limit
            if prov == "polygon":
                _throttle_polygon()
            obb = _get_obb()
            result = obb.equity.price.historical(
                symbol=ticker,
                start_date=from_date,
                end_date=to_date,
                provider=prov,
            )
            return result.to_df()

        df = _retry(_fetch, label=f"price_historical({ticker})")

        if df is None or df.empty:
            logger.warning(f"[obb_price_historical] '{ticker}' returned no data")
            return pd.DataFrame()

        # Rename to yfinance-style capitalized columns
        rename_map = {
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        }
        df = df.rename(columns=rename_map)

        # Ensure DatetimeIndex
        if df.index.name == "date" and not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df.index.name = "Date"

        # Keep only standard columns
        keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[keep_cols].sort_index()

        _cache_set(key, df.copy())
        logger.debug(f"[obb_price_historical] '{ticker}' fetched {len(df)} bars via {prov}")
        return df

    except Exception as e:
        logger.warning(f"[obb_price_historical] '{ticker}' failed: {e}")
        return pd.DataFrame()


def obb_fred_series(
    series_ids: Union[str, List[str]],
    observation_start: Optional[str] = None,
    cache_ttl: Optional[int] = None,
) -> Dict[str, pd.Series]:
    """
    Fetch FRED economic data series via OpenBB.

    Drop-in replacement for fred_get_series(). Supports batch-fetching
    multiple series in a single API call.

    Args:
        series_ids: Single series ID or list (e.g. ["SP500", "VIXCLS"])
        observation_start: Start date (YYYY-MM-DD)
        cache_ttl: Cache TTL override in seconds

    Returns:
        Dict mapping series_id -> pd.Series with DatetimeIndex.
        Missing/failed series are omitted from the result.
    """
    if isinstance(series_ids, str):
        series_ids = [series_ids]

    # Check cache for each series
    result_dict: Dict[str, pd.Series] = {}
    missing = []
    for sid in series_ids:
        key = _cache_key("fred_series", series_id=sid, start=observation_start or "")
        cached = _cache_get(key, cache_ttl)
        if cached is not None:
            result_dict[sid] = cached.copy()
        else:
            missing.append(sid)

    if not missing:
        logger.debug(f"[obb_fred_series] All {len(series_ids)} series from cache")
        return result_dict

    # Batch fetch missing series
    symbol_str = ",".join(missing)
    still_missing = list(missing)
    try:
        def _fetch():
            obb = _get_obb()
            kwargs = {"symbol": symbol_str, "provider": _get_provider("macro")}
            if observation_start:
                kwargs["start_date"] = observation_start
            result = obb.economy.fred_series(**kwargs)
            return result.to_df()

        df = _retry(_fetch, label=f"fred_series({symbol_str})")

        if df is not None and not df.empty:
            # OBB returns DataFrame with date index, one column per series
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            for sid in missing:
                if sid in df.columns:
                    series = df[sid].dropna()
                    if len(series) > 0:
                        result_dict[sid] = series
                        cache_k = _cache_key("fred_series", series_id=sid, start=observation_start or "")
                        _cache_set(cache_k, series.copy())
                        still_missing.remove(sid)
                        logger.debug(f"[obb_fred_series] '{sid}' fetched {len(series)} points")
                    else:
                        logger.debug(f"[obb_fred_series] '{sid}' returned empty in batch")
                else:
                    logger.debug(f"[obb_fred_series] '{sid}' not found in batch response")

    except Exception as e:
        logger.warning(f"[obb_fred_series] Batch fetch failed for {symbol_str}: {e}")

    # Fallback: fetch individually any series dropped from the batch response
    for sid in still_missing:
        try:
            def _fetch_single(series_id=sid):
                obb = _get_obb()
                kwargs = {"symbol": series_id, "provider": _get_provider("macro")}
                if observation_start:
                    kwargs["start_date"] = observation_start
                result = obb.economy.fred_series(**kwargs)
                return result.to_df()

            single_df = _retry(_fetch_single, max_retries=2, label=f"fred_series({sid})")
            if single_df is not None and not single_df.empty:
                if not isinstance(single_df.index, pd.DatetimeIndex):
                    single_df.index = pd.to_datetime(single_df.index)
                # Column may be named after the series ID or be the only column
                if sid in single_df.columns:
                    col = sid
                elif len(single_df.columns) == 1:
                    col = single_df.columns[0]
                else:
                    logger.debug(f"[obb_fred_series] '{sid}' individual fetch: unexpected columns {list(single_df.columns)}")
                    continue
                series = single_df[col].dropna()
                if len(series) > 0:
                    result_dict[sid] = series
                    cache_k = _cache_key("fred_series", series_id=sid, start=observation_start or "")
                    _cache_set(cache_k, series.copy())
                    logger.debug(f"[obb_fred_series] '{sid}' fetched {len(series)} points (individual fallback)")
        except Exception as e:
            logger.warning(f"[obb_fred_series] '{sid}' individual fetch failed: {e}")

    return result_dict


def obb_financial_ratios(
    ticker: str,
    provider: Optional[str] = None,
    cache_ttl: Optional[int] = None,
) -> dict:
    """
    Fetch financial ratios via OpenBB.

    Drop-in replacement for massive_financials_ratios(). Returns dict
    with keys compatible with FundamentalModule field lookups.

    Args:
        ticker: US stock ticker
        provider: OBB provider override
        cache_ttl: Cache TTL override

    Returns:
        Dict with financial ratio fields, or empty dict on failure
    """
    key = _cache_key("financial_ratios", ticker=ticker)
    cached = _cache_get(key, cache_ttl)
    if cached is not None:
        logger.debug(f"[obb_financial_ratios] Cache hit: '{ticker}'")
        return cached.copy()

    prov = provider or _get_provider("fundamental")

    try:
        def _fetch():
            obb = _get_obb()
            result = obb.equity.fundamental.ratios(symbol=ticker, provider=prov)
            return result.to_df()

        df = _retry(_fetch, label=f"financial_ratios({ticker})")

        if df is None or df.empty:
            logger.warning(f"[obb_financial_ratios] '{ticker}' returned no data")
            return {}

        # Take the first row (TTM)
        row = df.iloc[0].to_dict()

        # Map to Massive-compatible keys that FundamentalModule expects
        mapped = {
            "price_to_earnings": row.get("price_to_earnings"),
            "price_to_sales": row.get("price_to_sales"),
            "debt_to_equity": row.get("debt_to_equity"),
            "current": row.get("current_ratio"),
            "free_cash_flow": row.get("free_cash_flow_per_share"),
            # Additional fields available from FMP ratios
            "gross_profit_margin": row.get("gross_profit_margin"),
            "operating_profit_margin": row.get("operating_profit_margin"),
            "net_profit_margin": row.get("net_profit_margin"),
            "dividend_yield": row.get("dividend_yield"),
            "price_to_book": row.get("price_to_book"),
        }

        _cache_set(key, mapped.copy())
        logger.debug(f"[obb_financial_ratios] '{ticker}' fetched via {prov}")
        return mapped

    except Exception as e:
        logger.warning(f"[obb_financial_ratios] '{ticker}' failed: {e}")
        return {}


def obb_income_statements(
    ticker: str,
    limit: int = 2,
    provider: Optional[str] = None,
    cache_ttl: Optional[int] = None,
) -> list:
    """
    Fetch income statements via OpenBB.

    Drop-in replacement for massive_income_statements(). Returns list of
    dicts (most recent first) with keys compatible with FundamentalModule.

    Args:
        ticker: US stock ticker
        limit: Number of periods to fetch
        provider: OBB provider override
        cache_ttl: Cache TTL override

    Returns:
        List of dicts with income statement fields, or empty list on failure
    """
    key = _cache_key("income_statements", ticker=ticker, limit=limit)
    cached = _cache_get(key, cache_ttl)
    if cached is not None:
        logger.debug(f"[obb_income_statements] Cache hit: '{ticker}'")
        return cached.copy()

    prov = provider or _get_provider("fundamental")

    try:
        def _fetch():
            obb = _get_obb()
            result = obb.equity.fundamental.income(
                symbol=ticker, limit=limit, period="annual", provider=prov
            )
            return result.to_df()

        df = _retry(_fetch, label=f"income_statements({ticker})")

        if df is None or df.empty:
            logger.warning(f"[obb_income_statements] '{ticker}' returned no data")
            return []

        # Convert each row to dict with Massive-compatible keys
        statements = []
        for _, row in df.iterrows():
            raw = row.to_dict()
            mapped = {
                "revenue": raw.get("revenue"),
                "gross_profit": raw.get("gross_profit"),
                "operating_income": raw.get("total_operating_income"),
                "consolidated_net_income_loss": raw.get("consolidated_net_income"),
                "basic_earnings_per_share": raw.get("basic_earnings_per_share"),
                "fiscal_year": raw.get("fiscal_year"),
                "fiscal_period": raw.get("fiscal_period"),
                "period_ending": str(raw.get("period_ending", "")),
            }
            statements.append(mapped)

        _cache_set(key, statements.copy())
        logger.debug(f"[obb_income_statements] '{ticker}' fetched {len(statements)} periods via {prov}")
        return statements

    except Exception as e:
        logger.warning(f"[obb_income_statements] '{ticker}' failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Nasdaq earnings calendar (shared cache for all tickers within one session)
# ---------------------------------------------------------------------------
_nasdaq_calendar_cache_key = "nasdaq_earnings_global"


def _fetch_nasdaq_earnings_calendar(cache_ttl: Optional[int] = None) -> pd.DataFrame:
    """
    Fetch the Nasdaq earnings calendar (today to +30 days).
    Cached globally so multiple tickers share a single API call.

    Note: Nasdaq API is most reliable within a 30-day window.
    Stocks with earnings beyond this window will not appear.
    """
    cached = _cache_get(_nasdaq_calendar_cache_key, cache_ttl)
    if cached is not None:
        return cached

    today = date.today()
    start = today.isoformat()
    end = (today + timedelta(days=30)).isoformat()

    for attempt in range(3):
        try:
            obb = _get_obb()
            df = obb.equity.calendar.earnings(
                provider="nasdaq",
                start_date=start,
                end_date=end,
            ).to_df()
            if df is not None and not df.empty:
                _cache_set(_nasdaq_calendar_cache_key, df)
                logger.debug(f"[nasdaq_earnings] Fetched {len(df)} entries (today to +30d)")
                return df
        except Exception as e:
            logger.debug(f"[nasdaq_earnings] Attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(3)

    return pd.DataFrame()


def obb_earnings_calendar(
    ticker: str,
    limit: int = 4,
    provider: Optional[str] = None,
    cache_ttl: Optional[int] = None,
) -> list:
    """
    Fetch earnings dates for a specific ticker.

    Uses Nasdaq earnings calendar via OBB (global fetch, filter by symbol).
    One API call serves all tickers within the same session.

    Args:
        ticker: US stock ticker
        limit: Max results to return
        provider: Unused (kept for API compatibility)
        cache_ttl: Cache TTL override

    Returns:
        List of dicts with earnings date info, or empty list on failure
    """
    key = _cache_key("earnings_calendar", ticker=ticker)
    cached = _cache_get(key, cache_ttl)
    if cached is not None:
        logger.debug(f"[obb_earnings_calendar] Cache hit: '{ticker}'")
        return cached.copy()

    earnings = []

    # Nasdaq earnings calendar (one global call, filter by symbol)
    nasdaq_df = _fetch_nasdaq_earnings_calendar(cache_ttl=cache_ttl)
    if not nasdaq_df.empty and "symbol" in nasdaq_df.columns:
        filtered = nasdaq_df[nasdaq_df["symbol"].str.upper() == ticker.upper()]
        if not filtered.empty:
            for _, row in filtered.iterrows():
                raw = row.to_dict()
                earnings.append({
                    "date": str(raw.get("report_date", "")),
                    "estimated_eps": raw.get("eps_consensus"),
                    "actual_eps": raw.get("eps_actual"),
                    "estimated_revenue": raw.get("revenue_consensus"),
                    "actual_revenue": raw.get("revenue_actual"),
                })
            logger.debug(f"[obb_earnings_calendar] '{ticker}' found {len(earnings)} in Nasdaq calendar")

    if not earnings:
        logger.debug(f"[obb_earnings_calendar] '{ticker}' not found in Nasdaq calendar")
        return []

    # Sort by date descending, take up to limit
    earnings.sort(key=lambda x: x.get("date", ""), reverse=True)
    result = earnings[:limit]
    _cache_set(key, result)
    return result


def obb_analyst_consensus(
    ticker: str,
    cache_ttl: Optional[int] = None,
) -> dict:
    """
    Fetch analyst consensus data via OpenBB + Alpha Vantage.

    Combines:
    - FMP estimates.consensus for price targets (reliable)
    - AV NEWS_SENTIMENT for news-based sentiment signal (replaces yfinance)

    Returns dict with same keys as Benzinga consensus for backward compatibility.

    Args:
        ticker: US stock ticker
        cache_ttl: Cache TTL override

    Returns:
        Dict with consensus data, or empty dict on failure
    """
    key = _cache_key("analyst_consensus", ticker=ticker)
    cached = _cache_get(key, cache_ttl)
    if cached is not None:
        logger.debug(f"[obb_analyst_consensus] Cache hit: '{ticker}'")
        return cached.copy()

    result = {}

    # 1. FMP consensus for price targets (reliable)
    try:
        def _fetch_targets():
            obb = _get_obb()
            r = obb.equity.estimates.consensus(symbol=ticker, provider="fmp")
            return r.to_df()

        df = _retry(_fetch_targets, label=f"consensus_targets({ticker})")
        if df is not None and not df.empty:
            row = df.iloc[0].to_dict()
            result["consensus_price_target"] = row.get("target_consensus")
            result["high_price_target"] = row.get("target_high")
            result["low_price_target"] = row.get("target_low")
    except Exception as e:
        logger.debug(f"[obb_analyst_consensus] FMP targets for '{ticker}' failed: {e}")

    # 2. AV NEWS_SENTIMENT for sentiment-based rating signal (replaces yfinance)
    try:
        news = av_news_sentiment(ticker, limit=50, cache_ttl=cache_ttl)
        if news and news.get("total_scored", 0) >= 5:
            pos = news["positive_count"]
            neg = news["negative_count"]
            neu = news["neutral_count"]
            total = pos + neg + neu
            avg = news["avg_sentiment"]

            # Map AV sentiment score (-1 to 1) to recommendation_mean (1-5 scale)
            # AV: >= 0.35 Bullish, 0.15-0.35 Somewhat-Bullish, -0.15-0.15 Neutral,
            #     -0.35--0.15 Somewhat-Bearish, <= -0.35 Bearish
            if avg >= 0.30:
                rec_mean = 1.5  # Strong Buy
            elif avg >= 0.15:
                rec_mean = 2.0  # Buy
            elif avg >= 0.05:
                rec_mean = 2.5  # Moderate Buy
            elif avg >= -0.05:
                rec_mean = 3.0  # Hold
            elif avg >= -0.15:
                rec_mean = 3.5  # Moderate Sell
            elif avg >= -0.30:
                rec_mean = 4.0  # Sell
            else:
                rec_mean = 4.5  # Strong Sell

            result["strong_buy_ratings"] = pos
            result["buy_ratings"] = 0
            result["hold_ratings"] = neu
            result["sell_ratings"] = neg
            result["strong_sell_ratings"] = 0
            result["recommendation_mean"] = rec_mean
            result["num_analysts"] = total
            result["news_sentiment_score"] = avg
    except Exception as e:
        logger.debug(f"[obb_analyst_consensus] AV news sentiment for '{ticker}' failed: {e}")

    if result:
        _cache_set(key, result.copy())
        logger.debug(f"[obb_analyst_consensus] '{ticker}' consensus assembled")

    return result
