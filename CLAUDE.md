# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered stock analysis system for A-shares (Chinese market), Hong Kong stocks, and US stocks. It fetches market data from multiple sources, performs technical analysis, uses AI models (Gemini/OpenAI) to generate scored recommendations with buy/sell signals, and dispatches results via 10+ notification channels. Includes a FastAPI backend, React web UI, and GitHub Actions automation.

## Commands

### Running the application

```bash
python main.py                            # Normal run (uses STOCK_LIST from .env)
python main.py --stocks 600519,000001     # Analyze specific stocks
python main.py --market-review            # Market review only
python main.py --webui                    # Start Web UI + auto-analysis
python main.py --serve-only              # FastAPI server only (no auto-analysis)
python main.py --backtest                 # Run backtest engine
python main.py --debug                    # Debug mode
python main.py --dry-run                  # Data fetch only, no AI analysis
python main.py --schedule                 # Scheduled mode
```

### Testing

```bash
./test.sh syntax        # Python syntax check (py_compile)
./test.sh flake8        # Static analysis (critical errors only)
./test.sh code          # Stock code recognition unit tests
./test.sh yfinance      # YFinance code conversion unit tests
./test.sh quick         # Quick single-stock test (needs API keys)
./test.sh a-stock       # A-share analysis test
./test.sh us-stock      # US stock analysis test
./test.sh hk-stock      # HK stock analysis test
./test.sh all           # Run all tests
```

### Code quality

```bash
black --line-length 120 <files>
isort --profile black --line-length 120 <files>
flake8 <files> --max-line-length=120
python -m py_compile <file>               # Quick syntax check
```

### Docker

```bash
docker build -t stock-analysis:test -f docker/Dockerfile .
docker-compose -f docker/docker-compose.yml up -d
```

### Frontend (apps/dsa-web)

```bash
cd apps/dsa-web && npm install && npm run dev    # Development
cd apps/dsa-web && npm run build                 # Production build
```

## Architecture

### Core Pipeline Flow

```
main.py → StockAnalysisPipeline (src/core/pipeline.py)
  1. Data fetching: DataFetcherManager with priority-based fallback across 6 providers
  2. Technical analysis: StockTrendAnalyzer (MA5>MA10>MA20 trend trading)
  3. News search: SearchService (Tavily/SerpAPI/Brave/Bocha with load balancing)
  4. AI analysis: GeminiAnalyzer (Gemini or OpenAI-compatible, generates JSON scores/signals)
  5. Storage: DatabaseManager (SQLite via SQLAlchemy ORM)
  6. Notification: NotificationService (dispatches to all configured channels)
```

### Directory Structure

- **`src/core/`** — Pipeline orchestrator, market review, backtest engine, config manager
- **`src/`** — Core modules: `analyzer.py` (AI), `notification.py` (dispatch), `storage.py` (ORM models), `stock_analyzer.py` (technical indicators), `search_service.py`, `config.py` (singleton)
- **`src/services/`** — Business logic layer: analysis, backtest, history, stock, system config, task queue
- **`src/repositories/`** — Data access layer: analysis_repo, backtest_repo, stock_repo
- **`data_provider/`** — Multi-source data fetchers with common `base.py` interface. Priority: efinance(0) → akshare(1) → tushare(2) → pytdx(2) → baostock(3) → yfinance(4)
- **`api/`** — FastAPI app with `v1/endpoints/` (analysis, stocks, history, backtest, config)
- **`bot/`** — Chat platform integrations (DingTalk, Feishu, Discord) with command dispatcher
- **`apps/dsa-web/`** — React 19 + Vite 7 + TypeScript + Tailwind CSS 4 frontend
- **`apps/dsa-desktop/`** — Electron desktop wrapper

### Key Patterns

- **Config singleton** (`src/config.py`): All settings loaded from `.env`, validated at startup. See `.env.example` for ~60 configurable variables.
- **Data provider fallback**: Each fetcher in `data_provider/` has a priority. The manager tries them in order, falling back on failure.
- **Concurrent analysis**: `ThreadPoolExecutor` with configurable `MAX_WORKERS` for parallel stock processing.
- **Retry/resilience**: Uses `tenacity` for exponential backoff on API calls. Search service has built-in load balancing across API keys.
- **Stock code conventions**: A-shares use 6-digit codes (600519), HK stocks are prefixed `hk` (hk00700), US stocks use ticker symbols (AAPL).

## Code Style

- **Python 3.10+**, line width **120 characters**
- Formatting: `black` + `isort` (profile=black) + `flake8`
- flake8 ignores: E501, W503, E203, E402 (see `setup.cfg`)
- New/modified code comments must be in **English**
- Commit messages must be in **English**
- Do not add `Co-Authored-By` tags to commits (per AGENTS.md)
- Do not commit without explicit user confirmation

## Release Tags

Use these tags in commit messages to control auto-versioning:
- `#patch` — bug fixes, small changes
- `#minor` — new features, backward compatible
- `#major` — breaking changes
- `#skip` / `#none` — no version tag
