# Personal Stock Portfolio Tracker

A self-contained stock portfolio tracker with a lightweight Python backend, responsive frontend, live quote fallbacks, and Playwright end-to-end coverage.

## Features

- Watchlist for major tickers such as `AAPL`, `GOOGL`, `TSLA`, `MSFT`, and `NVDA`
- Quote fetching with a provider chain:
  - `yfinance` when available
  - Yahoo Finance quote endpoint fallback
  - Playwright scraping fallback
  - deterministic demo data fallback for known symbols
- Portfolio holdings management:
  - add holdings
  - edit holdings
  - delete holdings
- Portfolio metrics:
  - total value
  - total cost basis
  - unrealized profit/loss
  - daily move based on previous close
- Manual refresh plus auto-refresh every 5 minutes
- Dark/light mode toggle with persistence
- Responsive layout for desktop and mobile
- Playwright end-to-end test

## Tech Stack

- Backend: Python standard library HTTP server
- Frontend: plain HTML, CSS, and JavaScript
- Browser automation/tests: Playwright

## Project Structure

```text
.
├── public/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scripts/
│   └── scrape-quotes.mjs
├── tests/
│   └── portfolio.spec.js
├── playwright.config.js
├── package.json
├── requirements.txt
└── server.py
```

## Requirements

- Python 3.9+
- Node.js 20+ recommended
- npm
- Google Chrome installed locally if you want to use the system-Chrome Playwright path used by this project

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Node dependencies

```bash
npm install
```

## Run the App

### Mock/demo mode

Mock mode is useful for deterministic demos and test assertions.

```bash
PORTFOLIO_DATA_MODE=mock python3 server.py
```

Open:

```text
http://127.0.0.1:8000
```

### Live-data mode

```bash
python3 server.py
```

In live mode, the app tries providers in this order:

1. `yfinance`
2. Yahoo Finance quote endpoint
3. Playwright scraping
4. demo fallback for known symbols

## Run Tests

```bash
npx playwright test
```

The Playwright config starts the local server automatically in mock mode.

## Notes on Data Providers

- `yfinance` is preferred but optional at runtime.
- If `yfinance` is not installed or unavailable, the app falls back to public quote retrieval and then to Playwright scraping.
- Playwright scraping is slower and more brittle than API-based retrieval, but it keeps the app functional when the preferred provider is unavailable.

## Demo Flow

Recommended demo sequence:

1. Start the app in mock mode.
2. Add `AAPL` and `MSFT`.
3. Refresh prices.
4. Toggle dark mode.
5. Edit one holding.
6. Delete one holding.
7. Resize to mobile width.
8. Run the Playwright suite.

## What This Demo Demonstrates

This repository is a good demo of:

- Complex coding on a non-trivial app built from scratch
- Agentic workflow execution across planning, implementation, debugging, and verification
- Playwright test generation and browser automation
- Visible browser operation for a live UI workflow
- Resilient fallback logic when preferred market-data providers are unavailable

In practical terms, this demo shows:

- a complete working app
- a deterministic mock mode for repeatable tests and recordings
- a live-data mode with provider fallback behavior
- a passing Playwright test suite entry point
- a browser-driven demo flow covering add, edit, delete, refresh, theme toggle, and responsive resize

## What This Demo Does Not Demonstrate

This repository is not strong evidence for:

- deep web research or multi-source synthesis
- large tool-search ecosystems or MCP-style tool selection
- 1M-context or very long-context workflows
- spreadsheet, document, or presentation generation
- explicit token-efficiency or `/fast` mode measurement
- custom confirmation-policy tuning

It only partially demonstrates:

- computer use beyond the browser
- screenshot-driven interaction
- native desktop-style automation across arbitrary applications

The browser automation here is primarily Playwright-based web interaction, which is strong evidence for browser-task execution, but not a full proof of generalized desktop computer use.

## Known Limitations

- This is a lightweight local project, not a production-grade deployment setup.
- Live quote sources may change behavior or rate-limit requests.
- Holdings are stored in browser local storage, not a database.
- The Playwright scraping fallback depends on the target site structure remaining stable.

## Suggested Next Improvements

- Add charts and allocation breakdowns
- Add CSV import/export
- Add server-side holdings persistence
- Add caching and rate-limit handling for quote providers
- Expand Playwright coverage for edit/delete/theme persistence/mobile layout
