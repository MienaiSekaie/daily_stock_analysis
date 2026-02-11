# -*- coding: utf-8 -*-
"""
Stock → Sector ETF Mapping

~50 popular US stocks mapped to their primary sector ETF.
For stocks not in this map, falls back to yfinance info['sector']
matched to the closest sector ETF.
"""

# Sector ETFs used for comparison
SECTOR_ETFS = [
    "XLK",   # Technology
    "XLF",   # Financials
    "XLE",   # Energy
    "XLV",   # Health Care
    "XLI",   # Industrials
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLU",   # Utilities
    "XLRE",  # Real Estate
    "XLC",   # Communication Services
    "XLB",   # Materials
    "SMH",   # Semiconductors
]

# Mapping from yfinance sector names to ETFs
SECTOR_NAME_TO_ETF = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Energy": "XLE",
    "Healthcare": "XLV",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Consumer Cyclical": "XLY",
    "Consumer Discretionary": "XLY",
    "Consumer Defensive": "XLP",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
    "Basic Materials": "XLB",
    "Materials": "XLB",
}

# ~50 popular US stocks with sector ETF and peer group
SECTOR_MAP = {
    # === Technology / Software ===
    "AAPL": {"etf": "XLK", "sector": "Technology", "sub_sector": "Consumer Electronics"},
    "MSFT": {"etf": "XLK", "sector": "Technology", "sub_sector": "Software"},
    "GOOGL": {"etf": "XLC", "sector": "Communication Services", "sub_sector": "Internet"},
    "GOOG": {"etf": "XLC", "sector": "Communication Services", "sub_sector": "Internet"},
    "META": {"etf": "XLC", "sector": "Communication Services", "sub_sector": "Social Media"},
    "NFLX": {"etf": "XLC", "sector": "Communication Services", "sub_sector": "Streaming"},
    "CRM": {"etf": "XLK", "sector": "Technology", "sub_sector": "Software"},
    "ORCL": {"etf": "XLK", "sector": "Technology", "sub_sector": "Software"},
    "ADBE": {"etf": "XLK", "sector": "Technology", "sub_sector": "Software"},

    # === Semiconductors ===
    "NVDA": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "AMD": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "INTC": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "AVGO": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "QCOM": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "TSM": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "MU": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "ASML": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},
    "ARM": {"etf": "SMH", "sector": "Technology", "sub_sector": "Semiconductors"},

    # === Consumer / E-commerce ===
    "AMZN": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "E-commerce"},
    "TSLA": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "EV/Auto"},
    "NKE": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "Apparel"},
    "SBUX": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "Restaurants"},
    "HD": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "Home Improvement"},
    "COST": {"etf": "XLP", "sector": "Consumer Staples", "sub_sector": "Retail"},
    "WMT": {"etf": "XLP", "sector": "Consumer Staples", "sub_sector": "Retail"},
    "PG": {"etf": "XLP", "sector": "Consumer Staples", "sub_sector": "Household Products"},
    "KO": {"etf": "XLP", "sector": "Consumer Staples", "sub_sector": "Beverages"},
    "PEP": {"etf": "XLP", "sector": "Consumer Staples", "sub_sector": "Beverages"},

    # === Financials ===
    "JPM": {"etf": "XLF", "sector": "Financials", "sub_sector": "Banks"},
    "BAC": {"etf": "XLF", "sector": "Financials", "sub_sector": "Banks"},
    "GS": {"etf": "XLF", "sector": "Financials", "sub_sector": "Investment Banking"},
    "V": {"etf": "XLF", "sector": "Financials", "sub_sector": "Payments"},
    "MA": {"etf": "XLF", "sector": "Financials", "sub_sector": "Payments"},
    "BRK.B": {"etf": "XLF", "sector": "Financials", "sub_sector": "Insurance/Conglomerate"},

    # === Healthcare / Pharma ===
    "JNJ": {"etf": "XLV", "sector": "Healthcare", "sub_sector": "Pharma"},
    "UNH": {"etf": "XLV", "sector": "Healthcare", "sub_sector": "Health Insurance"},
    "PFE": {"etf": "XLV", "sector": "Healthcare", "sub_sector": "Pharma"},
    "LLY": {"etf": "XLV", "sector": "Healthcare", "sub_sector": "Pharma"},
    "ABBV": {"etf": "XLV", "sector": "Healthcare", "sub_sector": "Biotech"},
    "MRK": {"etf": "XLV", "sector": "Healthcare", "sub_sector": "Pharma"},

    # === Energy ===
    "XOM": {"etf": "XLE", "sector": "Energy", "sub_sector": "Oil & Gas"},
    "CVX": {"etf": "XLE", "sector": "Energy", "sub_sector": "Oil & Gas"},

    # === Industrials ===
    "BA": {"etf": "XLI", "sector": "Industrials", "sub_sector": "Aerospace"},
    "CAT": {"etf": "XLI", "sector": "Industrials", "sub_sector": "Machinery"},
    "GE": {"etf": "XLI", "sector": "Industrials", "sub_sector": "Conglomerate"},

    # === Chinese ADR ===
    "BABA": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "E-commerce/China"},
    "PDD": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "E-commerce/China"},
    "JD": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "E-commerce/China"},
    "BIDU": {"etf": "XLC", "sector": "Communication Services", "sub_sector": "Internet/China"},
    "NIO": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "EV/China"},
    "XPEV": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "EV/China"},
    "LI": {"etf": "XLY", "sector": "Consumer Discretionary", "sub_sector": "EV/China"},

    # === Crypto-related ===
    "COIN": {"etf": "XLF", "sector": "Financials", "sub_sector": "Crypto Exchange"},
    "MSTR": {"etf": "XLK", "sector": "Technology", "sub_sector": "Crypto/Software"},
}

# Peer groups for sector ranking (stocks commonly compared together)
SECTOR_PEERS = {
    "SMH": ["NVDA", "AMD", "INTC", "AVGO", "QCOM", "TSM", "MU", "ASML", "ARM"],
    "XLK": ["AAPL", "MSFT", "CRM", "ORCL", "ADBE"],
    "XLC": ["GOOGL", "META", "NFLX", "BIDU"],
    "XLY": ["AMZN", "TSLA", "NKE", "SBUX", "HD"],
    "XLP": ["COST", "WMT", "PG", "KO", "PEP"],
    "XLF": ["JPM", "BAC", "GS", "V", "MA"],
    "XLV": ["JNJ", "UNH", "PFE", "LLY", "ABBV", "MRK"],
    "XLE": ["XOM", "CVX"],
    "XLI": ["BA", "CAT", "GE"],
}


def get_sector_info(code: str) -> dict:
    """
    Get sector info for a stock.

    Returns dict with 'etf', 'sector', 'sub_sector'.
    Falls back to yfinance lookup for unmapped stocks.
    """
    if code in SECTOR_MAP:
        return SECTOR_MAP[code]

    # Fallback: try yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(code).info
        sector = info.get("sector", "")
        etf = SECTOR_NAME_TO_ETF.get(sector, "XLK")  # Default to XLK
        return {
            "etf": etf,
            "sector": sector or "Unknown",
            "sub_sector": info.get("industry", "Unknown"),
        }
    except Exception:
        return {"etf": "XLK", "sector": "Unknown", "sub_sector": "Unknown"}


def get_sector_peers(etf: str) -> list:
    """Get peer stocks for a given sector ETF."""
    return SECTOR_PEERS.get(etf, [])
