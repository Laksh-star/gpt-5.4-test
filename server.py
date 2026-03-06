#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).parent
PUBLIC_DIR = ROOT / "public"
DEFAULT_SYMBOLS = ["AAPL", "GOOGL", "TSLA", "MSFT", "NVDA"]
PORTFOLIO_SAMPLE_HOLDINGS = [
    {"ticker": "AAPL", "shares": 10, "avgPrice": 180.0},
    {"ticker": "MSFT", "shares": 5, "avgPrice": 300.0},
    {"ticker": "NVDA", "shares": 2, "avgPrice": 800.0},
]
MOCK_QUOTES = {
    "AAPL": {"price": 210.00, "previousClose": 205.00, "currency": "USD", "name": "Apple"},
    "GOOGL": {"price": 172.50, "previousClose": 170.00, "currency": "USD", "name": "Alphabet"},
    "TSLA": {"price": 245.25, "previousClose": 250.00, "currency": "USD", "name": "Tesla"},
    "MSFT": {"price": 418.10, "previousClose": 414.00, "currency": "USD", "name": "Microsoft"},
    "NVDA": {"price": 912.40, "previousClose": 900.00, "currency": "USD", "name": "NVIDIA"},
}
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}
TOOL_SEARCH_CATALOG = [
    {
        "id": "market-data",
        "name": "Market Data",
        "description": "Price, range, and event lookups for equities and sector context.",
        "tools": [
            {
                "id": "quote_lookup",
                "name": "Quote Lookup",
                "description": "Return the latest mocked quote, previous close, and currency for one or more tickers so downstream steps can compute value, daily move, and price context without external dependencies.",
            },
            {
                "id": "historical_range",
                "name": "Historical Range",
                "description": "Provide a deterministic 30-day high/low range plus midpoint commentary for a single ticker to support narrative summaries and context sections.",
            },
            {
                "id": "compare_tickers",
                "name": "Compare Tickers",
                "description": "Compare selected tickers on price change, relative strength, and directional trend so a reporting layer can explain leaders and laggards.",
            },
            {
                "id": "top_movers",
                "name": "Top Movers",
                "description": "Return a local, deterministic list of notable movers in the mocked universe for watchlist-style summary sections.",
            },
            {
                "id": "earnings_date",
                "name": "Earnings Date",
                "description": "Expose the next mocked earnings date and timing window so reports can mention upcoming catalysts and event risk.",
            },
            {
                "id": "sector_snapshot",
                "name": "Sector Snapshot",
                "description": "Provide a brief deterministic sector summary, benchmark context, and relative tone for the requested ticker group.",
            },
            {
                "id": "dividend_info",
                "name": "Dividend Info",
                "description": "Return deterministic dividend yield and payout notes to support longer-form investment summaries.",
            },
            {
                "id": "volatility_snapshot",
                "name": "Volatility Snapshot",
                "description": "Return local risk labels, recent range expansion commentary, and a compact volatility rating for portfolio and research narratives.",
            },
        ],
    },
    {
        "id": "portfolio-analytics",
        "name": "Portfolio Analytics",
        "description": "Allocation, gains, exposures, and portfolio-specific analytics computed from deterministic sample holdings.",
        "tools": [
            {
                "id": "allocation_breakdown",
                "name": "Allocation Breakdown",
                "description": "Calculate position weights, dominant holdings, and share of total portfolio value to support allocation summaries and charts.",
            },
            {
                "id": "gain_loss_summary",
                "name": "Gain/Loss Summary",
                "description": "Compute unrealized gains and losses against average buy price using mocked quotes so reports can discuss total P/L and top contributors.",
            },
            {
                "id": "rebalance_suggestion",
                "name": "Rebalance Suggestion",
                "description": "Generate a deterministic rebalance note when a position exceeds a simple concentration threshold or when winners dominate the book.",
            },
            {
                "id": "concentration_risk",
                "name": "Concentration Risk",
                "description": "Assess concentration using local thresholds, identify the largest positions, and describe the risk in plain language.",
            },
            {
                "id": "benchmark_compare",
                "name": "Benchmark Compare",
                "description": "Compare the mocked portfolio move with a deterministic benchmark move to support executive summary wording.",
            },
            {
                "id": "scenario_analysis",
                "name": "Scenario Analysis",
                "description": "Apply a simple stress scenario across holdings and return downside commentary that can be reused in risk memos.",
            },
            {
                "id": "exposure_summary",
                "name": "Exposure Summary",
                "description": "Summarize sector and single-name exposure using local category mappings for narrative reporting and risk checks.",
            },
            {
                "id": "holdings_snapshot",
                "name": "Holdings Snapshot",
                "description": "Return a compact structured snapshot of mocked holdings, shares, prices, and value to seed downstream reporting tools.",
            },
        ],
    },
    {
        "id": "news-research",
        "name": "News Research",
        "description": "Mocked research summaries, catalysts, and risk notes for deterministic research-style workflows.",
        "tools": [
            {
                "id": "headline_summary",
                "name": "Headline Summary",
                "description": "Produce a deterministic set of recent headline bullets and directional framing for a given ticker without live web requests.",
            },
            {
                "id": "sentiment_summary",
                "name": "Sentiment Summary",
                "description": "Return a local positive/neutral/cautious sentiment mix to support quick memo writing and research notes.",
            },
            {
                "id": "catalyst_extraction",
                "name": "Catalyst Extraction",
                "description": "Extract deterministic near-term catalysts such as launches, guidance updates, or macro dependencies for the requested ticker.",
            },
            {
                "id": "peer_scan",
                "name": "Peer Scan",
                "description": "Compare the ticker against deterministic peer names to help frame positioning, relative momentum, and watchlist context.",
            },
            {
                "id": "macro_calendar",
                "name": "Macro Calendar",
                "description": "Return upcoming macro events that could influence the mocked ticker narrative in a research note.",
            },
            {
                "id": "filing_summary",
                "name": "Filing Summary",
                "description": "Provide a deterministic filing-style digest with management commentary themes and operational focus areas.",
            },
            {
                "id": "analyst_notes_summary",
                "name": "Analyst Notes Summary",
                "description": "Summarize mocked analyst takes, target direction, and areas of consensus or disagreement for narrative research output.",
            },
            {
                "id": "risk_factor_summary",
                "name": "Risk Factor Summary",
                "description": "Return a compact set of operating, valuation, and macro risks so a memo can balance upside with downside framing.",
            },
        ],
    },
    {
        "id": "reporting",
        "name": "Reporting",
        "description": "Formatting and packaging tools for converting structured data into deliverables such as memos, digests, and previews.",
        "tools": [
            {
                "id": "markdown_memo",
                "name": "Markdown Memo",
                "description": "Assemble a structured markdown memo from supplied analytics and commentary blocks with consistent headings and executive framing.",
            },
            {
                "id": "email_summary",
                "name": "Email Summary",
                "description": "Format a concise email-ready summary with bullets, subject line, and key decisions for stakeholders.",
            },
            {
                "id": "alert_digest",
                "name": "Alert Digest",
                "description": "Create a compact alert digest with changes, notable items, and action flags that can be pasted into chat or email.",
            },
            {
                "id": "watchlist_note",
                "name": "Watchlist Note",
                "description": "Generate a short watchlist note highlighting what changed, what matters next, and what to monitor.",
            },
            {
                "id": "executive_summary",
                "name": "Executive Summary",
                "description": "Produce an executive-style summary paragraph and supporting bullets suitable for dashboard and presentation front matter.",
            },
            {
                "id": "csv_export_preview",
                "name": "CSV Export Preview",
                "description": "Return a deterministic CSV preview string from structured rows so the workflow can show export readiness without creating files.",
            },
            {
                "id": "slide_outline_draft",
                "name": "Slide Outline Draft",
                "description": "Convert an analysis into a short presentation outline with title, key slide points, and takeaways.",
            },
            {
                "id": "json_export_preview",
                "name": "JSON Export Preview",
                "description": "Return a compact JSON preview of structured results to simulate downstream API or export packaging.",
            },
        ],
    },
]
TOOL_SEARCH_SCENARIOS = [
    {
        "id": "daily-portfolio-brief",
        "name": "Daily Portfolio Brief",
        "description": "Summarize current portfolio value, concentration, and market context in an executive-ready daily note.",
        "steps": [
            {"serverId": "market-data", "toolId": "quote_lookup"},
            {"serverId": "market-data", "toolId": "top_movers"},
            {"serverId": "portfolio-analytics", "toolId": "holdings_snapshot"},
            {"serverId": "portfolio-analytics", "toolId": "gain_loss_summary"},
            {"serverId": "portfolio-analytics", "toolId": "allocation_breakdown"},
            {"serverId": "reporting", "toolId": "executive_summary"},
            {"serverId": "reporting", "toolId": "markdown_memo"},
        ],
    },
    {
        "id": "ticker-research-note",
        "name": "Ticker Research Note",
        "description": "Generate a compact research-style note for a tracked name using price context, catalysts, and sentiment.",
        "steps": [
            {"serverId": "market-data", "toolId": "quote_lookup"},
            {"serverId": "market-data", "toolId": "historical_range"},
            {"serverId": "news-research", "toolId": "headline_summary"},
            {"serverId": "news-research", "toolId": "catalyst_extraction"},
            {"serverId": "news-research", "toolId": "risk_factor_summary"},
            {"serverId": "reporting", "toolId": "watchlist_note"},
            {"serverId": "reporting", "toolId": "markdown_memo"},
        ],
    },
    {
        "id": "risk-rebalance-check",
        "name": "Risk & Rebalance Check",
        "description": "Assess portfolio concentration and produce a rebalance-oriented action note.",
        "steps": [
            {"serverId": "portfolio-analytics", "toolId": "holdings_snapshot"},
            {"serverId": "portfolio-analytics", "toolId": "concentration_risk"},
            {"serverId": "portfolio-analytics", "toolId": "rebalance_suggestion"},
            {"serverId": "portfolio-analytics", "toolId": "scenario_analysis"},
            {"serverId": "reporting", "toolId": "alert_digest"},
            {"serverId": "reporting", "toolId": "markdown_memo"},
        ],
    },
]
SERVER_LOOKUP = {server["id"]: server for server in TOOL_SEARCH_CATALOG}
SCENARIO_LOOKUP = {scenario["id"]: scenario for scenario in TOOL_SEARCH_SCENARIOS}


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_with_yfinance(symbols):
    try:
        import yfinance as yf
    except ImportError:
        return {}

    quotes = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = _safe_float(getattr(info, "last_price", None))
            previous_close = _safe_float(getattr(info, "previous_close", None))

            if price is None:
                history = ticker.history(period="2d", interval="1d", auto_adjust=False)
                if not history.empty:
                    closes = history["Close"].dropna().tolist()
                    if closes:
                        price = _safe_float(closes[-1])
                        previous_close = _safe_float(closes[-2] if len(closes) > 1 else closes[-1])

            if price is None:
                continue

            quotes[symbol] = {
                "symbol": symbol,
                "name": ticker.info.get("shortName") if getattr(ticker, "info", None) else symbol,
                "price": price,
                "previousClose": previous_close or price,
                "currency": "USD",
                "source": "yfinance",
            }
        except Exception:
            continue
    return quotes


def fetch_with_yahoo_endpoint(symbols):
    if not symbols:
        return {}

    base_url = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = urlencode({"symbols": ",".join(symbols)})
    request = Request(
        f"{base_url}?{params}",
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError):
        return {}

    results = {}
    quote_response = payload.get("quoteResponse", {})
    for entry in quote_response.get("result", []) or []:
        symbol = entry.get("symbol")
        if not symbol:
            continue
        price = _safe_float(entry.get("regularMarketPrice"))
        previous_close = _safe_float(entry.get("regularMarketPreviousClose"))
        if price is None:
            continue
        results[symbol] = {
            "symbol": symbol,
            "name": entry.get("shortName") or symbol,
            "price": price,
            "previousClose": previous_close or price,
            "currency": entry.get("currency") or "USD",
            "source": "yahoo-chart",
        }
    return results


def fetch_with_playwright(symbols):
    script = ROOT / "scripts" / "scrape-quotes.mjs"
    if not script.exists():
        return {}

    try:
        result = subprocess.run(
            ["node", str(script), *symbols],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=45,
            check=True,
        )
    except Exception:
        return {}

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    quotes = {}
    for symbol, item in payload.items():
        price = _safe_float(item.get("price"))
        previous_close = _safe_float(item.get("previousClose"))
        if price is None:
            continue
        quotes[symbol] = {
            "symbol": symbol,
            "name": item.get("name") or symbol,
            "price": price,
            "previousClose": previous_close or price,
            "currency": item.get("currency") or "USD",
            "source": "playwright-scrape",
        }
    return quotes


def fetch_quotes(symbols, force_mock=False):
    unique_symbols = []
    seen = set()
    for symbol in symbols or DEFAULT_SYMBOLS:
        upper = symbol.strip().upper()
        if upper and upper not in seen:
            seen.add(upper)
            unique_symbols.append(upper)

    if force_mock or os.getenv("PORTFOLIO_DATA_MODE", "").lower() == "mock":
        return build_mock_quotes(unique_symbols)

    providers = [fetch_with_yfinance, fetch_with_yahoo_endpoint, fetch_with_playwright]
    merged = {}
    for provider in providers:
        merged.update(provider([symbol for symbol in unique_symbols if symbol not in merged]))
        if len(merged) == len(unique_symbols):
            break

    for symbol in unique_symbols:
        if symbol not in merged and symbol in MOCK_QUOTES:
            quote = MOCK_QUOTES[symbol]
            merged[symbol] = {
                "symbol": symbol,
                "name": quote["name"],
                "price": quote["price"],
                "previousClose": quote["previousClose"],
                "currency": quote["currency"],
                "source": "demo-fallback",
            }

    return merged


def build_mock_quotes(symbols):
    quotes = {}
    for symbol in symbols:
        quote = MOCK_QUOTES.get(
            symbol,
            {"price": 100.0, "previousClose": 99.0, "currency": "USD", "name": symbol},
        )
        quotes[symbol] = {
            "symbol": symbol,
            "name": quote["name"],
            "price": quote["price"],
            "previousClose": quote["previousClose"],
            "currency": quote["currency"],
            "source": "mock",
        }
    return quotes


def _tool_definition_bytes(tool):
    return len(json.dumps(tool, sort_keys=True))


def _server_tool_map():
    tool_map = {}
    for server in TOOL_SEARCH_CATALOG:
        tool_map[server["id"]] = {tool["id"]: tool for tool in server["tools"]}
    return tool_map


TOOL_LOOKUP = _server_tool_map()


def _portfolio_context():
    quotes = build_mock_quotes([holding["ticker"] for holding in PORTFOLIO_SAMPLE_HOLDINGS])
    positions = []
    total_value = 0.0
    total_cost = 0.0
    total_daily_move = 0.0

    for holding in PORTFOLIO_SAMPLE_HOLDINGS:
        quote = quotes[holding["ticker"]]
        market_value = quote["price"] * holding["shares"]
        cost_basis = holding["avgPrice"] * holding["shares"]
        daily_move = (quote["price"] - quote["previousClose"]) * holding["shares"]
        position = {
            "ticker": holding["ticker"],
            "name": quote["name"],
            "shares": holding["shares"],
            "avgPrice": holding["avgPrice"],
            "price": quote["price"],
            "previousClose": quote["previousClose"],
            "marketValue": round(market_value, 2),
            "costBasis": round(cost_basis, 2),
            "profitLoss": round(market_value - cost_basis, 2),
            "dailyMove": round(daily_move, 2),
        }
        positions.append(position)
        total_value += market_value
        total_cost += cost_basis
        total_daily_move += daily_move

    for position in positions:
        position["weightPct"] = round((position["marketValue"] / total_value) * 100, 2) if total_value else 0.0

    return {
        "holdings": positions,
        "totalValue": round(total_value, 2),
        "totalCost": round(total_cost, 2),
        "totalProfitLoss": round(total_value - total_cost, 2),
        "totalDailyMove": round(total_daily_move, 2),
    }


def _format_currency(value):
    return f"${value:,.2f}"


def _format_percent(value):
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def run_mock_tool(server_id, tool_id, context):
    portfolio = context["portfolio"]
    quotes = context["quotes"]
    primary_ticker = context.get("primaryTicker", "NVDA")
    primary_quote = quotes[primary_ticker]
    top_holding = max(portfolio["holdings"], key=lambda position: position["marketValue"])

    if server_id == "market-data" and tool_id == "quote_lookup":
        watch = ["AAPL", "MSFT", "NVDA"]
        return {
            "quotes": {ticker: quotes[ticker] for ticker in watch},
            "headline": f"{primary_ticker} trades at {_format_currency(primary_quote['price'])} after a {_format_percent(((primary_quote['price'] - primary_quote['previousClose']) / primary_quote['previousClose']) * 100)} move versus the prior close.",
        }
    if server_id == "market-data" and tool_id == "top_movers":
        return {
            "movers": [
                {"ticker": "NVDA", "movePct": 1.38},
                {"ticker": "AAPL", "movePct": 2.44},
                {"ticker": "TSLA", "movePct": -1.90},
            ]
        }
    if server_id == "market-data" and tool_id == "historical_range":
        return {
            "ticker": primary_ticker,
            "range": {"low": 884.00, "high": 938.50},
            "note": f"{primary_ticker} remains in the upper half of its mocked 30-day range, supporting a constructive but elevated-risk tone.",
        }
    if server_id == "portfolio-analytics" and tool_id == "holdings_snapshot":
        return {
            "holdings": portfolio["holdings"],
            "totalValue": portfolio["totalValue"],
            "totalCost": portfolio["totalCost"],
        }
    if server_id == "portfolio-analytics" and tool_id == "gain_loss_summary":
        winner = max(portfolio["holdings"], key=lambda position: position["profitLoss"])
        return {
            "totalProfitLoss": portfolio["totalProfitLoss"],
            "dailyMove": portfolio["totalDailyMove"],
            "topWinner": winner["ticker"],
            "summary": f"Portfolio P/L stands at {_format_currency(portfolio['totalProfitLoss'])}, led by {winner['ticker']} as the strongest unrealized contributor.",
        }
    if server_id == "portfolio-analytics" and tool_id == "allocation_breakdown":
        return {
            "weights": [{position["ticker"]: position["weightPct"]} for position in portfolio["holdings"]],
            "largestPosition": top_holding["ticker"],
            "largestWeightPct": top_holding["weightPct"],
        }
    if server_id == "portfolio-analytics" and tool_id == "concentration_risk":
        label = "Elevated" if top_holding["weightPct"] >= 45 else "Moderate"
        return {
            "riskLevel": label,
            "largestPosition": top_holding["ticker"],
            "weightPct": top_holding["weightPct"],
            "note": f"{label} concentration risk because {top_holding['ticker']} represents {top_holding['weightPct']:.2f}% of total market value.",
        }
    if server_id == "portfolio-analytics" and tool_id == "rebalance_suggestion":
        return {
            "action": f"Trim {top_holding['ticker']} toward a sub-40% weight and rotate proceeds into MSFT or cash to reduce single-name dependence.",
        }
    if server_id == "portfolio-analytics" and tool_id == "scenario_analysis":
        downside = round(portfolio["totalValue"] * 0.08, 2)
        return {
            "stressMove": -8,
            "estimatedDrawdown": downside,
            "commentary": f"An 8% broad pullback would reduce the mocked portfolio by about {_format_currency(downside)}.",
        }
    if server_id == "news-research" and tool_id == "headline_summary":
        return {
            "ticker": primary_ticker,
            "headlines": [
                f"{primary_ticker} supplier commentary points to stable near-term demand.",
                f"Investors remain focused on {primary_ticker} margin durability into the next earnings cycle.",
            ],
        }
    if server_id == "news-research" and tool_id == "catalyst_extraction":
        return {
            "catalysts": [
                "next earnings print",
                "guidance update",
                "AI infrastructure demand commentary",
            ]
        }
    if server_id == "news-research" and tool_id == "risk_factor_summary":
        return {
            "risks": [
                "valuation compression if growth moderates",
                "macro spending slowdown",
                "execution risk around supply and capacity",
            ]
        }
    if server_id == "reporting" and tool_id == "executive_summary":
        return {
            "summary": f"The mocked portfolio is worth {_format_currency(portfolio['totalValue'])}, with {top_holding['ticker']} as the largest position and total unrealized P/L at {_format_currency(portfolio['totalProfitLoss'])}.",
        }
    if server_id == "reporting" and tool_id == "watchlist_note":
        return {
            "summary": f"{primary_ticker} remains on watch after holding above {_format_currency(primary_quote['price'])}; near-term framing stays constructive but risk-aware.",
        }
    if server_id == "reporting" and tool_id == "alert_digest":
        return {
            "summary": f"Concentration check flags {top_holding['ticker']} as the primary rebalance candidate with {top_holding['weightPct']:.2f}% weight.",
        }
    if server_id == "reporting" and tool_id == "markdown_memo":
        scenario_id = context["scenario"]["id"]
        if scenario_id == "daily-portfolio-brief":
            return {
                "memo": "\n".join(
                    [
                        "# Daily Portfolio Brief",
                        "",
                        f"- Total value: {_format_currency(portfolio['totalValue'])}",
                        f"- Unrealized P/L: {_format_currency(portfolio['totalProfitLoss'])}",
                        f"- Largest position: {top_holding['ticker']} at {top_holding['weightPct']:.2f}%",
                        "- Takeaway: the book remains constructive, but concentration should stay under review.",
                    ]
                )
            }
        if scenario_id == "ticker-research-note":
            return {
                "memo": "\n".join(
                    [
                        f"# {primary_ticker} Research Note",
                        "",
                        f"- Current price: {_format_currency(primary_quote['price'])}",
                        "- Near-term catalysts: earnings, guidance, infrastructure demand commentary",
                        "- Key risks: valuation compression, macro softness, execution",
                        "- Takeaway: maintain watchlist status with a constructive but selective tone.",
                    ]
                )
            }
        return {
            "memo": "\n".join(
                [
                    "# Risk & Rebalance Check",
                    "",
                    f"- Largest position: {top_holding['ticker']} at {top_holding['weightPct']:.2f}%",
                    f"- Total portfolio value: {_format_currency(portfolio['totalValue'])}",
                    "- Suggested action: trim concentration and preserve optionality.",
                    "- Stress framing: an 8% pullback would create a manageable but visible drawdown.",
                ]
            )
        }

    raise KeyError(f"Unknown tool: {server_id}.{tool_id}")


def list_tool_search_servers():
    return [
        {
            "id": server["id"],
            "name": server["name"],
            "description": server["description"],
            "toolCount": len(server["tools"]),
        }
        for server in TOOL_SEARCH_CATALOG
    ]


def list_tool_search_scenarios():
    return [
        {
            "id": scenario["id"],
            "name": scenario["name"],
            "description": scenario["description"],
            "requiredServers": sorted({step["serverId"] for step in scenario["steps"]}),
        }
        for scenario in TOOL_SEARCH_SCENARIOS
    ]


def run_tool_search_scenario(mode, scenario_id):
    if mode not in {"eager", "search"}:
        raise ValueError("mode must be 'eager' or 'search'")
    if scenario_id not in SCENARIO_LOOKUP:
        raise KeyError("unknown scenario")

    scenario = SCENARIO_LOOKUP[scenario_id]
    context = {
        "scenario": scenario,
        "portfolio": _portfolio_context(),
        "quotes": build_mock_quotes(DEFAULT_SYMBOLS),
        "primaryTicker": "NVDA",
    }
    trace = []
    loaded_servers = set()
    loaded_tools = set()
    definition_bytes_loaded = 0
    tool_calls = 0
    search_steps = 0

    if mode == "eager":
        for server in TOOL_SEARCH_CATALOG:
            for tool in server["tools"]:
                loaded_tools.add((server["id"], tool["id"]))
                definition_bytes_loaded += _tool_definition_bytes(tool)
        trace.append(
            {
                "type": "catalog",
                "target": "all-servers",
                "detail": f"Loaded all {sum(len(server['tools']) for server in TOOL_SEARCH_CATALOG)} tool definitions before execution.",
            }
        )
    else:
        trace.append(
            {
                "type": "catalog",
                "target": "server-catalog",
                "detail": f"Loaded lightweight catalog for {len(TOOL_SEARCH_CATALOG)} servers and selected tools on demand.",
            }
        )
        search_steps += 1

    last_result = {}
    for step in scenario["steps"]:
        server = SERVER_LOOKUP[step["serverId"]]
        tool = TOOL_LOOKUP[step["serverId"]][step["toolId"]]

        if mode == "search" and server["id"] not in loaded_servers:
            loaded_servers.add(server["id"])
            trace.append(
                {
                    "type": "load_server",
                    "target": server["name"],
                    "detail": f"Loaded server definition for {server['name']} with {len(server['tools'])} available tools.",
                }
            )
            search_steps += 1

        if mode == "search" and (server["id"], tool["id"]) not in loaded_tools:
            loaded_tools.add((server["id"], tool["id"]))
            definition_bytes_loaded += _tool_definition_bytes(tool)
            trace.append(
                {
                    "type": "load_tool",
                    "target": tool["name"],
                    "detail": f"Loaded tool definition for {tool['name']} only when the scenario required it.",
                }
            )
            search_steps += 1

        tool_calls += 1
        result = run_mock_tool(server["id"], tool["id"], context)
        context["lastResult"] = result
        context[f"{server['id']}:{tool['id']}"] = result
        last_result = result
        trace.append(
            {
                "type": "tool_call",
                "target": f"{server['name']} / {tool['name']}",
                "detail": f"Executed {tool['name']} and produced deterministic local output for the scenario.",
            }
        )

    output = last_result.get("memo") or last_result.get("summary") or json.dumps(last_result, indent=2)
    summary = f"{scenario['name']} completed successfully in {mode} mode."
    trace.append(
        {
            "type": "result",
            "target": scenario["name"],
            "detail": f"Scenario finished with the same final deliverable shape while loading {len(loaded_tools)} tool definitions.",
        }
    )

    simulated_elapsed_ms = 65 + (tool_calls * 14) + (search_steps * 9)
    if mode == "eager":
        simulated_elapsed_ms += 75

    return {
        "scenarioId": scenario["id"],
        "mode": mode,
        "success": True,
        "summary": summary,
        "output": output,
        "metrics": {
            "serversAvailable": len(TOOL_SEARCH_CATALOG),
            "toolsAvailable": sum(len(server["tools"]) for server in TOOL_SEARCH_CATALOG),
            "toolDefinitionsLoaded": len(loaded_tools),
            "definitionBytesLoaded": definition_bytes_loaded,
            "toolCalls": tool_calls,
            "searchSteps": search_steps,
            "elapsedMs": simulated_elapsed_ms,
        },
        "trace": trace,
    }


class PortfolioHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/quotes":
            query = parse_qs(parsed.query)
            symbols = []
            if "symbols" in query:
                symbols = query["symbols"][0].split(",")
            force_mock = query.get("mock", ["0"])[0] == "1"
            quotes = fetch_quotes(symbols or DEFAULT_SYMBOLS, force_mock=force_mock)
            body = {
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "quotes": quotes,
            }
            return self.send_json(body)

        if path == "/api/health":
            return self.send_json({"ok": True, "time": datetime.now(timezone.utc).isoformat()})

        if path == "/api/tool-search/servers":
            return self.send_json({"servers": list_tool_search_servers()})

        if path == "/api/tool-search/scenarios":
            return self.send_json({"scenarios": list_tool_search_scenarios()})

        return self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/tool-search/run":
            payload = self.read_json()
            if not payload:
                return self.send_json({"error": "JSON body is required."}, status=400)
            try:
                result = run_tool_search_scenario(payload.get("mode"), payload.get("scenarioId"))
            except ValueError as error:
                return self.send_json({"error": str(error)}, status=400)
            except KeyError as error:
                return self.send_json({"error": str(error)}, status=404)
            return self.send_json(result)

        return self.send_json({"error": "Not found"}, status=404)

    def serve_static(self, path):
        if path in ("/", ""):
            relative = "index.html"
        elif path in ("/tool-search-lab", "/tool-search-lab/"):
            relative = "tool-search-lab.html"
        else:
            relative = path.lstrip("/")
        file_path = (PUBLIC_DIR / relative).resolve()

        if PUBLIC_DIR not in file_path.parents and file_path != PUBLIC_DIR / "index.html":
            self.send_error(404)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        content_type = CONTENT_TYPES.get(file_path.suffix, "application/octet-stream")
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return None
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def log_message(self, format, *args):
        return


def main():
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), PortfolioHandler)
    print(f"Portfolio tracker running at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
