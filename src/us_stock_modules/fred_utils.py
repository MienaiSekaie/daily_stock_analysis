# -*- coding: utf-8 -*-
"""
DEPRECATED: Use openbb_utils.py instead.

This module is retained for backward compatibility. All new code should
use obb_fred_series() from openbb_utils.py.
"""

import warnings
warnings.warn(
    "fred_utils is deprecated, use openbb_utils.obb_fred_series() instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

import logging
import os
import threading
import time
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache (shared across all modules within one process)
# ---------------------------------------------------------------------------
_series_cache: dict = {}  # series_id+params -> (timestamp, Series)
_cache_lock = threading.Lock()
_DEFAULT_CACHE_TTL = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Lazy-initialized Fred client singleton
# ---------------------------------------------------------------------------
_fred_client = None
_client_lock = threading.Lock()


def _get_client():
    """Get or create the Fred client singleton."""
    global _fred_client
    if _fred_client is None:
        with _client_lock:
            if _fred_client is None:
                from fredapi import Fred

                api_key = os.getenv("FRED_API_KEY")
                if not api_key:
                    raise ValueError(
                        "FRED_API_KEY environment variable is not set. "
                        "Please set it in your .env file."
                    )
                # Build proxies dict, filtering out None values to avoid
                # TypeError in urllib when only HTTP_PROXY is set but not HTTPS_PROXY
                http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
                https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
                proxies = {}
                if http_proxy:
                    proxies["http"] = http_proxy
                if https_proxy:
                    proxies["https"] = https_proxy
                elif http_proxy:
                    # FRED API uses HTTPS; fall back to HTTP proxy for HTTPS if not set
                    proxies["https"] = http_proxy

                _fred_client = Fred(api_key=api_key, proxies=proxies if proxies else None)
                logger.info("[fred_utils] Fred client initialized")
    return _fred_client


def _cache_key(series_id: str, **kwargs) -> str:
    """Build a hashable cache key."""
    parts = [series_id]
    for k in sorted(kwargs.keys()):
        if kwargs[k] is not None:
            parts.append(f"{k}={kwargs[k]}")
    return "|".join(parts)


def clear_cache():
    """Clear all cached data (useful between sessions)."""
    global _series_cache
    with _cache_lock:
        _series_cache.clear()
    logger.debug("[fred_utils] Cache cleared")


# ---------------------------------------------------------------------------
# fred_get_series — cached wrapper
# ---------------------------------------------------------------------------
def fred_get_series(
    series_id: str,
    observation_start: Optional[str] = None,
    observation_end: Optional[str] = None,
    max_retries: int = 3,
    cache_ttl: int = _DEFAULT_CACHE_TTL,
) -> pd.Series:
    """
    Cached wrapper around Fred.get_series().

    Args:
        series_id: FRED series ID (e.g. "SP500", "VIXCLS", "DGS10", "DTWEXBGS")
        observation_start: Start date string (YYYY-MM-DD), optional
        observation_end: End date string (YYYY-MM-DD), optional
        max_retries: Number of retry attempts
        cache_ttl: Cache duration in seconds (0 to disable)

    Returns:
        pandas.Series with DatetimeIndex and float values, or empty Series on failure
    """
    # Check cache
    key = _cache_key(series_id, start=observation_start, end=observation_end)
    if cache_ttl > 0:
        with _cache_lock:
            if key in _series_cache:
                cached_time, cached_series = _series_cache[key]
                if time.time() - cached_time < cache_ttl:
                    logger.debug(f"[fred_get_series] Cache hit: '{series_id}'")
                    return cached_series.copy()

    for attempt in range(max_retries):
        try:
            client = _get_client()

            kwargs = {}
            if observation_start:
                kwargs["observation_start"] = observation_start
            if observation_end:
                kwargs["observation_end"] = observation_end

            data = client.get_series(series_id, **kwargs)

            if data is not None and len(data) > 0:
                # Drop NaN values (FRED uses '.' for missing data, converted to NaN)
                data = data.dropna()
                if len(data) > 0:
                    # Cache successful result
                    if cache_ttl > 0:
                        with _cache_lock:
                            _series_cache[key] = (time.time(), data.copy())
                    logger.debug(f"[fred_get_series] '{series_id}' fetched {len(data)} observations")
                    return data

            # Empty result — retry
            if attempt < max_retries - 1:
                wait = 2**attempt * 2  # 2s, 4s
                logger.debug(
                    f"[fred_get_series] Empty result for '{series_id}', "
                    f"retry {attempt + 1}/{max_retries} after {wait}s"
                )
                time.sleep(wait)
                continue

            logger.warning(f"[fred_get_series] '{series_id}' returned no data")
            return pd.Series(dtype=float)

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2**attempt * 2
                logger.debug(
                    f"[fred_get_series] '{series_id}' failed: {e}, "
                    f"retry {attempt + 1}/{max_retries} after {wait}s"
                )
                time.sleep(wait)
            else:
                logger.warning(f"[fred_get_series] '{series_id}' failed: {e}")
                return pd.Series(dtype=float)

    logger.warning(f"[fred_get_series] '{series_id}' failed after {max_retries} retries")
    return pd.Series(dtype=float)
