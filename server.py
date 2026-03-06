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

        return self.serve_static(path)

    def serve_static(self, path):
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
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
