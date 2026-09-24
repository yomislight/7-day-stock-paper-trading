#!/usr/bin/env python3
"""Legacy optional Alpaca check; the active runtime uses public_market_data_check."""

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "10-API密钥-仅本地-local-secrets" / "alpaca-market-data.env"
ALLOWED_BASE = "https://data.alpaca.markets"
ALLOWED_FEEDS = {"iex", "sip", "delayed_sip", "boats", "overnight"}
ALLOWED_KEYS = {
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_DATA_BASE_URL",
    "ALPACA_DATA_FEED",
    "ALPACA_SYMBOLS",
    "ALPACA_MAX_AGE_SECONDS",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_config(path):
    values = {}
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key not in ALLOWED_KEYS or key in values:
            raise ValueError("Invalid or duplicate setting at line %d" % number)
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Unclosed quote at line %d" % number)
            value = value[1:-1]
        if any(character.isspace() for character in value) or not value.isascii():
            raise ValueError("Invalid setting format at line %d" % number)
        values[key] = value
    values.setdefault("ALPACA_DATA_BASE_URL", ALLOWED_BASE)
    values.setdefault("ALPACA_DATA_FEED", "iex")
    values.setdefault("ALPACA_SYMBOLS", "SPY,QQQ,DIA,IWM,AAPL,NVDA,XOM,JPM")
    values.setdefault("ALPACA_MAX_AGE_SECONDS", "300")
    if values["ALPACA_DATA_BASE_URL"] != ALLOWED_BASE:
        raise ValueError("ALPACA_DATA_BASE_URL must be the official Market Data host")
    if values["ALPACA_DATA_FEED"] not in ALLOWED_FEEDS:
        raise ValueError("Unsupported Alpaca data feed")
    symbols = [item for item in values["ALPACA_SYMBOLS"].split(",") if item]
    if not symbols or any(not item.isalnum() or item != item.upper() for item in symbols):
        raise ValueError("ALPACA_SYMBOLS must be comma-separated uppercase tickers")
    try:
        max_age = int(values["ALPACA_MAX_AGE_SECONDS"])
    except ValueError:
        raise ValueError("ALPACA_MAX_AGE_SECONDS must be an integer") from None
    if not 60 <= max_age <= 900:
        raise ValueError("ALPACA_MAX_AGE_SECONDS must be between 60 and 900")
    return values


def get_json(url, headers):
    request = Request(url, headers={"User-Agent": "seven-day-paper-trading/2.0", **headers}, method="GET")
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            body = response.read()
        data = json.loads(body)
        return data if isinstance(data, dict) else None, None
    except HTTPError as exc:
        return None, "HTTP %d" % exc.code
    except (URLError, TimeoutError, OSError):
        return None, "Network or TLS error"
    except (ValueError, UnicodeError):
        return None, "Invalid JSON response"


def positive(value):
    try:
        parsed = Decimal(str(value))
        return parsed.is_finite() and parsed > 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def decimal_or_none(value):
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_timestamp(value):
    text = str(value or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "." in text:
        head, tail = text.split(".", 1)
        digits, separator, zone = tail.partition("+")
        if not separator:
            digits, separator, zone = tail.partition("-")
        if separator:
            text = head + "." + digits[:6] + separator + zone
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def check(config, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    key = config.get("ALPACA_API_KEY_ID", "")
    secret = config.get("ALPACA_API_SECRET_KEY", "")
    symbols = [item for item in config["ALPACA_SYMBOLS"].split(",") if item]
    result = {
        "checked_at": now.isoformat(),
        "provider": "alpaca_market_data",
        "base_url": ALLOWED_BASE,
        "feed": config["ALPACA_DATA_FEED"],
        "credentials_present": bool(key and secret),
        "requested_symbols": symbols,
        "verified_symbols": [],
        "quote_verified": False,
        "minute_volume_vwap_verified": False,
        "session_bars_verified": False,
        "recent_daily_volume_verified": False,
        "freshness_verified": False,
        "market_data_ready": False,
        "errors": [],
    }
    if not result["credentials_present"]:
        result["errors"].append("Fill the local Alpaca market-data credentials")
        return result
    query = urlencode({"symbols": ",".join(symbols), "feed": config["ALPACA_DATA_FEED"]})
    data, error = get_json(
        ALLOWED_BASE + "/v2/stocks/snapshots?" + query,
        {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
    )
    if error or not isinstance(data, dict):
        result["errors"].append("snapshots: " + (error or "Unexpected response"))
        return result
    snapshots = data.get("snapshots") if isinstance(data.get("snapshots"), dict) else data
    local = now.astimezone(ZoneInfo("America/Chicago"))
    session_open = local.replace(hour=8, minute=30, second=0, microsecond=0)
    if local < session_open:
        result["errors"].append("Regular-session bars are not available before 08:30 Central")
        return result
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    session_query = urlencode({
        "symbols": ",".join(symbols),
        "timeframe": "1Min",
        "start": session_open.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "end": now.isoformat().replace("+00:00", "Z"),
        "feed": config["ALPACA_DATA_FEED"],
        "adjustment": "raw",
        "sort": "asc",
        "limit": 10000,
    })
    session_data, session_error = get_json(ALLOWED_BASE + "/v2/stocks/bars?" + session_query, headers)
    if session_error or not isinstance(session_data, dict):
        result["errors"].append("session_bars: " + (session_error or "Unexpected response"))
        return result
    daily_query = urlencode({
        "symbols": ",".join(symbols),
        "timeframe": "1Day",
        "start": (now - timedelta(days=40)).date().isoformat(),
        "end": now.date().isoformat(),
        "feed": config["ALPACA_DATA_FEED"],
        "adjustment": "raw",
        "sort": "asc",
        "limit": 10000,
    })
    daily_data, daily_error = get_json(ALLOWED_BASE + "/v2/stocks/bars?" + daily_query, headers)
    if daily_error or not isinstance(daily_data, dict):
        result["errors"].append("daily_bars: " + (daily_error or "Unexpected response"))
        return result
    session_bars = session_data.get("bars") if isinstance(session_data.get("bars"), dict) else {}
    daily_bars = daily_data.get("bars") if isinstance(daily_data.get("bars"), dict) else {}
    max_age = int(config["ALPACA_MAX_AGE_SECONDS"])
    elapsed_minutes = max(1, min(390, int((local - session_open).total_seconds() // 60) + 1))
    safe = {}
    for symbol in symbols:
        snapshot = snapshots.get(symbol)
        if not isinstance(snapshot, dict):
            continue
        quote = snapshot.get("latestQuote")
        bar = snapshot.get("minuteBar")
        quote_ok = isinstance(quote, dict) and positive(quote.get("bp")) and positive(quote.get("ap"))
        bar_ok = isinstance(bar, dict) and positive(bar.get("v")) and positive(bar.get("vw"))
        timestamp = parse_timestamp(bar.get("t") if isinstance(bar, dict) else None)
        age = (now - timestamp).total_seconds() if timestamp else None
        fresh = age is not None and -2 <= age <= max_age
        bars = session_bars.get(symbol, [])
        bars = bars if isinstance(bars, list) else []
        weighted_sum = Decimal("0")
        session_volume = Decimal("0")
        for item in bars:
            if not isinstance(item, dict):
                continue
            volume = decimal_or_none(item.get("v"))
            vwap = decimal_or_none(item.get("vw"))
            if volume is not None and volume > 0 and vwap is not None and vwap > 0:
                session_volume += volume
                weighted_sum += volume * vwap
        session_vwap = weighted_sum / session_volume if session_volume > 0 else None
        history = daily_bars.get(symbol, [])
        history = history if isinstance(history, list) else []
        historical_volumes = []
        for item in history:
            if not isinstance(item, dict) or str(item.get("t", "")).startswith(local.date().isoformat()):
                continue
            volume = decimal_or_none(item.get("v"))
            if volume is not None and volume > 0:
                historical_volumes.append(volume)
        historical_volumes = historical_volumes[-20:]
        average_daily_volume = (
            sum(historical_volumes, Decimal("0")) / len(historical_volumes)
            if len(historical_volumes) >= 10 else None
        )
        average_minute_volume = average_daily_volume / Decimal("390") if average_daily_volume else None
        volume_pace_ratio = (
            (session_volume / elapsed_minutes) / average_minute_volume
            if average_minute_volume and average_minute_volume > 0 else None
        )
        session_ok = len(bars) > 0 and session_vwap is not None
        history_ok = average_daily_volume is not None
        if quote_ok and bar_ok and fresh and session_ok and history_ok:
            result["verified_symbols"].append(symbol)
        safe[symbol] = {
            "quote_ok": quote_ok,
            "minute_volume_vwap_ok": bar_ok,
            "fresh": fresh,
            "minute_bar_time": timestamp.isoformat() if timestamp else None,
            "minute_volume": bar.get("v") if isinstance(bar, dict) else None,
            "minute_vwap": bar.get("vw") if isinstance(bar, dict) else None,
            "session_bar_count": len(bars),
            "session_volume": str(session_volume),
            "session_vwap": str(session_vwap) if session_vwap is not None else None,
            "recent_average_daily_volume": (
                str(average_daily_volume) if average_daily_volume is not None else None
            ),
            "volume_pace_ratio": str(volume_pace_ratio) if volume_pace_ratio is not None else None,
        }
    result["symbols"] = safe
    result["quote_verified"] = bool(symbols) and all(safe.get(symbol, {}).get("quote_ok") for symbol in symbols)
    result["minute_volume_vwap_verified"] = bool(symbols) and all(
        safe.get(symbol, {}).get("minute_volume_vwap_ok") for symbol in symbols
    )
    result["freshness_verified"] = bool(symbols) and all(safe.get(symbol, {}).get("fresh") for symbol in symbols)
    result["session_bars_verified"] = bool(symbols) and all(
        safe.get(symbol, {}).get("session_bar_count", 0) > 0 for symbol in symbols
    )
    result["recent_daily_volume_verified"] = bool(symbols) and all(
        safe.get(symbol, {}).get("recent_average_daily_volume") is not None for symbol in symbols
    )
    result["market_data_ready"] = len(result["verified_symbols"]) == len(symbols)
    if not result["market_data_ready"]:
        result["errors"].append(
            "One or more symbols lack a fresh quote, session VWAP, volume pace, or sufficient daily history"
        )
    return result


def update_readiness(result):
    path = ROOT / "04-运行状态-state" / "readiness.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["supplemental_market_data"] = result
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--update-readiness", action="store_true")
    args = parser.parse_args()
    try:
        config = load_config(CONFIG)
        if args.check_config:
            present = bool(config.get("ALPACA_API_KEY_ID") and config.get("ALPACA_API_SECRET_KEY"))
            print(json.dumps({"config_valid": True, "credentials_present": present}))
            return 0 if present else 2
        result = check(config)
        if args.update_readiness:
            update_readiness(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["market_data_ready"]:
            return 0
        return 3 if any("Network" in error for error in result["errors"]) else 2
    except (OSError, ValueError):
        print(json.dumps({"error": "Check the local Alpaca config file and format; details suppressed"}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
