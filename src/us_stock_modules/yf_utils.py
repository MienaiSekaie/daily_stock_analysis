# -*- coding: utf-8 -*-
"""
Shared yfinance utilities for US stock modules.

Provides rate-limit-aware wrappers with retry and backoff to avoid
Yahoo Finance 429 errors when multiple modules run in parallel.
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Global rate limiter: ensures a minimum gap between yfinance calls
_lock = threading.Lock()
_last_call_time: float = 0.0
_MIN_INTERVAL: float = 1.0  # minimum seconds between yfinance calls


def _throttle():
    """Enforce minimum interval between yfinance API calls."""
    global _last_call_time
    with _lock:
        now = time.time()
        elapsed = now - _last_call_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_call_time = time.time()


def yf_download(tickers: str, max_retries: int = 3, **kwargs):
    """
    Rate-limited wrapper around yf.download() with retry on 429.

    Args:
        tickers: Ticker string (e.g. "SPY" or "AAPL MSFT SPY")
        max_retries: Number of retry attempts on rate limit errors
        **kwargs: Passed directly to yf.download()

    Returns:
        DataFrame from yf.download(), or empty DataFrame on failure
    """
    import yfinance as yf
    import pandas as pd

    # Default: suppress progress bar
    kwargs.setdefault("progress", False)
    kwargs.setdefault("auto_adjust", True)

    for attempt in range(max_retries):
        _throttle()
        try:
            data = yf.download(tickers, **kwargs)
            if data is not None and len(data) > 0:
                return data
            return pd.DataFrame()
        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "too many requests" in err_str or "429" in err_str:
                wait = 2 ** attempt * 2  # 2s, 4s, 8s
                logger.debug(f"[yf_download] Rate limited on '{tickers}', retry {attempt + 1}/{max_retries} after {wait}s")
                time.sleep(wait)
            else:
                logger.debug(f"[yf_download] '{tickers}' failed: {e}")
                return pd.DataFrame()

    logger.warning(f"[yf_download] '{tickers}' failed after {max_retries} retries (rate limited)")
    return pd.DataFrame()


def yf_ticker_info(code: str, max_retries: int = 3) -> dict:
    """
    Rate-limited wrapper to get yf.Ticker(code).info with retry on 429.

    Returns:
        info dict, or empty dict on failure
    """
    import yfinance as yf

    for attempt in range(max_retries):
        _throttle()
        try:
            ticker = yf.Ticker(code)
            info = ticker.info
            if info:
                return info
            return {}
        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "too many requests" in err_str or "429" in err_str:
                wait = 2 ** attempt * 2
                logger.debug(f"[yf_ticker_info] Rate limited on '{code}', retry {attempt + 1}/{max_retries} after {wait}s")
                time.sleep(wait)
            else:
                logger.debug(f"[yf_ticker_info] '{code}' failed: {e}")
                return {}

    logger.warning(f"[yf_ticker_info] '{code}' failed after {max_retries} retries")
    return {}


def yf_ticker(code: str, max_retries: int = 3) -> Optional[object]:
    """
    Rate-limited wrapper to create yf.Ticker with a pre-check.

    Returns:
        yf.Ticker object, or None on import failure
    """
    _throttle()
    try:
        import yfinance as yf
        return yf.Ticker(code)
    except Exception as e:
        logger.debug(f"[yf_ticker] Failed to create Ticker for '{code}': {e}")
        return None
