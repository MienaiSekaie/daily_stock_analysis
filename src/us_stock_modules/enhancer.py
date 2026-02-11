# -*- coding: utf-8 -*-
"""
US Stock Enhanced Analysis Orchestrator

Coordinates all 6 analysis modules, runs them in parallel via ThreadPoolExecutor,
and assembles a USStockAnalysisBundle for downstream AI prompt consumption.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

import pandas as pd

from src.us_stock_modules.multi_tf_technical_module import MultiTFTechnicalModule, MultiTFResult
from src.us_stock_modules.macro_module import MacroModule, MacroResult
from src.us_stock_modules.fundamental_module import FundamentalModule, FundamentalResult
from src.us_stock_modules.sector_module import SectorModule, SectorResult
from src.us_stock_modules.events_module import EventsModule, EventsResult
from src.us_stock_modules.sentiment_module import SentimentModule, SentimentResult

logger = logging.getLogger(__name__)


@dataclass
class USStockAnalysisBundle:
    """Aggregated results from all 6 US stock analysis modules."""

    technical: Optional[MultiTFResult] = None
    macro: Optional[Any] = None
    sector: Optional[Any] = None
    fundamental: Optional[Any] = None
    events: Optional[Any] = None
    sentiment: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all module results into a dict for context injection."""
        result = {}
        for module_name in ["technical", "macro", "sector", "fundamental", "events", "sentiment"]:
            module_result = getattr(self, module_name, None)
            if module_result is not None:
                if hasattr(module_result, "to_dict"):
                    result[module_name] = module_result.to_dict()
                elif hasattr(module_result, "__dataclass_fields__"):
                    result[module_name] = asdict(module_result)
                else:
                    result[module_name] = module_result
            else:
                result[module_name] = None
        return result

    def get_available_modules(self) -> list:
        """Return list of module names that have valid results."""
        available = []
        for name in ["technical", "macro", "sector", "fundamental", "events", "sentiment"]:
            if getattr(self, name, None) is not None:
                available.append(name)
        return available


class USStockEnhancer:
    """
    Orchestrator that runs all 6 US stock analysis modules in parallel.

    Usage:
        enhancer = USStockEnhancer(config)
        bundle = enhancer.analyze("AAPL", "Apple Inc.", daily_df)
        context['us_stock_bundle'] = bundle.to_dict()
    """

    def __init__(self, config):
        self.config = config
        self.technical = MultiTFTechnicalModule()
        # P1: Macro + Fundamental
        cache_ttl = getattr(config, "us_stock_macro_cache_ttl", 3600)
        self.macro = MacroModule(cache_ttl=cache_ttl)
        self.fundamental = FundamentalModule()
        # P2: Sector Context + Event Calendar
        self.sector = SectorModule()
        self.events = EventsModule()
        # P3: Sentiment & Flow
        self.sentiment = SentimentModule()

    def analyze(
        self,
        code: str,
        stock_name: str,
        daily_df: pd.DataFrame,
        news_context: Optional[str] = None,
    ) -> USStockAnalysisBundle:
        """
        Run all available modules in parallel and assemble results.

        Args:
            code: US stock ticker (e.g. "AAPL")
            stock_name: Stock name (e.g. "Apple Inc.")
            daily_df: DataFrame with daily OHLCV data (at least 60 rows recommended)
            news_context: Pre-formatted news text from SearchService

        Returns:
            USStockAnalysisBundle with all module results
        """
        logger.info(f"[{code}] Starting US stock enhanced analysis...")

        results = {}

        # Use max_workers=3 to limit concurrent yfinance requests and reduce 429 errors.
        # The global throttle in yf_utils.py enforces 0.5s gap between individual calls.
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            # Batch 1: Technical (local data, no yfinance) + Macro (cached, 1 call if cache hit)
            futures["technical"] = executor.submit(
                self._run_module, "technical", self.technical.analyze, code, daily_df
            )
            if self.macro is not None:
                futures["macro"] = executor.submit(
                    self._run_module, "macro", self.macro.analyze
                )

            # Batch 2: Stagger remaining yfinance-heavy modules with small delays
            if self.fundamental is not None:
                futures["fundamental"] = executor.submit(
                    self._run_module_delayed, "fundamental", 0.5, self.fundamental.analyze, code
                )
            if self.sector is not None:
                futures["sector"] = executor.submit(
                    self._run_module_delayed, "sector", 1.0, self.sector.analyze, code
                )
            if self.events is not None:
                futures["events"] = executor.submit(
                    self._run_module_delayed, "events", 1.5, self.events.analyze, code
                )
            if self.sentiment is not None:
                futures["sentiment"] = executor.submit(
                    self._run_module_delayed, "sentiment", 2.0, self.sentiment.analyze, code, news_context
                )

            # Collect results
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=60)
                except Exception as e:
                    logger.warning(f"[{code}] Module '{name}' timed out or failed: {e}")
                    results[name] = None

        bundle = USStockAnalysisBundle(**results)
        available = bundle.get_available_modules()
        logger.info(f"[{code}] US stock enhanced analysis done. Modules available: {available}")
        return bundle

    def _run_module(self, name: str, func, *args, **kwargs):
        """Run a single module with exception handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Module '{name}' failed: {e}")
            return None

    def _run_module_delayed(self, name: str, delay: float, func, *args, **kwargs):
        """Run a module after an initial delay to stagger yfinance requests."""
        time.sleep(delay)
        return self._run_module(name, func, *args, **kwargs)
