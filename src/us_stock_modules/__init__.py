# -*- coding: utf-8 -*-
"""
US Stock Enhanced Analysis Modules

Six-module analysis framework for US equities:
1. Macro Environment (Market Regime)
2. Sector Context
3. Fundamental Snapshot
4. Multi-Timeframe Technical Analysis
5. Event Calendar & Catalysts
6. Sentiment & Flow

Data sourced from Massive API (Polygon.io) and FRED. Modules run in
parallel and feed structured data into a US-stock-specific AI prompt.
"""

from src.us_stock_modules.enhancer import USStockEnhancer  # noqa: F401
from src.us_stock_modules.module_analyzer import USStockModuleAnalyzer  # noqa: F401

__all__ = ["USStockEnhancer", "USStockModuleAnalyzer"]
