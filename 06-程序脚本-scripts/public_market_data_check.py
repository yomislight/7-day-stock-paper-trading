#!/usr/bin/env python3
"""Validate keyless public intraday bars for paper-trading research only."""

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://query1.finance.yahoo.com"
DEFAULT_SYMBOLS = ("SPY", "QQQ", "DIA", "IWM", "AAPL", "NVDA", "XOM", "JPM")
INTERVAL = "5m"
RANGE = "1mo"
MAX_AGE_SECONDS = 1200
NEW_YORK = ZoneInfo("America/New_York")
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.-]{1,16}$")


def normalize_symbols(symbols):
    if isinstance(symbols, str):
        symbols = symbols.split(",")
    normalized = [str(item).strip().upper() for item in symbols if str(item).strip()]
    if not normalized or len(normalized) > 12:
        raise ValueError("Provide between 1 and 12 symbols")
    if len(set(normalized)) != len(normalized) or any(not SYMBOL_PATTERN.fullmatch(item) for item in normalized):
        raise ValueError("Symbols must be unique uppercase US-equity tickers")
    return normalized


def decimal_or_none(value):
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def get_json(symbol):
    query = urlencode({
        "range": RANGE,
        "interval": INTERVAL,
        "includePrePost": "false",
        "events": "div,splits",
    })
    url = BASE_URL + "/v8/finance/chart/" + quote(symbol, safe="") + "?" + query
    request = Request(url, headers={"User-Agent": "seven-day-paper-trading/3.0"}, method="GET")
    try:
        with urlopen(request, timeout=12) as response:
            data = json.loads(response.read())
        return data if isinstance(data, dict) else None, None
    except HTTPError as exc:
        return None, "HTTP %d" % exc.code
    except (URLError, TimeoutError, OSError):
        return None, "Network or TLS error"
    except (ValueError, UnicodeError):
        return None, "Invalid JSON response"


def chart_result(data):
    chart = data.get("chart") if isinstance(data, dict) else None
    if not isinstance(chart, dict) or chart.get("error"):
        return None
    results = chart.get("result")
    return results[0] if isinstance(results, list) and results and isinstance(results[0], dict) else None


def regular_bars(result):
    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    quotes = indicators.get("quote") if isinstance(indicators, dict) else None
    values = quotes[0] if isinstance(quotes, list) and quotes and isinstance(quotes[0], dict) else None
    if not isinstance(timestamps, list) or not isinstance(values, dict):
        return []
    arrays = {key: values.get(key) for key in ("open", "high", "low", "close", "volume")}
    if any(not isinstance(value, list) for value in arrays.values()):
        return []
    bars = []
    for index, stamp in enumerate(timestamps):
        if any(index >= len(value) for value in arrays.values()):
            continue
        try:
            moment = datetime.fromtimestamp(int(stamp), timezone.utc)
        except (OSError, OverflowError, TypeError, ValueError):
            continue
        local = moment.astimezone(NEW_YORK)
        if not time(9, 30) <= local.time().replace(tzinfo=None) <= time(16, 0):
            continue
        parsed = {key: decimal_or_none(value[index]) for key, value in arrays.items()}
        if parsed["close"] is None or parsed["close"] <= 0:
            continue
        bars.append({"timestamp": moment, "date": local.date(), **parsed})
    return bars


def summarize_symbol(data, now):
    result = chart_result(data)
    if result is None:
        return None
    bars = regular_bars(result)
    today = now.astimezone(NEW_YORK).date()
    current = [bar for bar in bars if bar["date"] == today and bar["volume"] is not None and bar["volume"] > 0]
    if not current:
        return {
            "fresh": False,
            "price_bar_ok": False,
            "session_volume_ok": False,
            "derived_vwap_ok": False,
            "history_ok": False,
            "data_gap": "No regular-session bar is available for the current New York trading date",
        }

    latest = current[-1]
    age_seconds = (now - latest["timestamp"]).total_seconds()
    fresh = -60 <= age_seconds <= MAX_AGE_SECONDS
    session_volume = sum((bar["volume"] for bar in current), Decimal("0"))
    weighted_sum = Decimal("0")
    weighted_volume = Decimal("0")
    for bar in current:
        high, low, close, volume = (bar[key] for key in ("high", "low", "close", "volume"))
        if all(value is not None and value > 0 for value in (high, low, close, volume)):
            typical_price = (high + low + close) / Decimal("3")
            weighted_sum += typical_price * volume
            weighted_volume += volume
    derived_vwap = weighted_sum / weighted_volume if weighted_volume > 0 else None

    daily_volumes = {}
    for bar in bars:
        if bar["date"] >= today or bar["volume"] is None or bar["volume"] <= 0:
            continue
        daily_volumes[bar["date"]] = daily_volumes.get(bar["date"], Decimal("0")) + bar["volume"]
    history = [daily_volumes[day] for day in sorted(daily_volumes)][-20:]
    average_daily_volume = sum(history, Decimal("0")) / len(history) if len(history) >= 10 else None

    session_open = datetime.combine(today, time(9, 30), NEW_YORK)
    elapsed_minutes = max(1, min(390, int((now.astimezone(NEW_YORK) - session_open).total_seconds() // 60) + 1))
    average_minute_volume = average_daily_volume / Decimal("390") if average_daily_volume else None
    volume_pace_ratio = (
        (session_volume / elapsed_minutes) / average_minute_volume
        if average_minute_volume and average_minute_volume > 0 else None
    )
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    previous_close = decimal_or_none(meta.get("chartPreviousClose") or meta.get("previousClose"))
    change_percent = (
        ((latest["close"] - previous_close) / previous_close) * Decimal("100")
        if previous_close and previous_close > 0 else None
    )
    return {
        "fresh": fresh,
        "price_bar_ok": latest["close"] > 0,
        "session_volume_ok": session_volume > 0,
        "derived_vwap_ok": derived_vwap is not None,
        "history_ok": average_daily_volume is not None,
        "latest_bar_time": latest["timestamp"].isoformat(),
        "latest_bar_age_seconds": int(age_seconds),
        "latest_close": str(latest["close"]),
        "previous_close": str(previous_close) if previous_close is not None else None,
        "change_percent_vs_previous_close": str(change_percent) if change_percent is not None else None,
        "session_bar_count": len(current),
        "session_volume": str(session_volume),
        "derived_session_vwap": str(derived_vwap) if derived_vwap is not None else None,
        "derived_vwap_method": "5-minute typical-price times volume; not an official exchange VWAP",
        "recent_average_daily_volume": str(average_daily_volume) if average_daily_volume is not None else None,
        "history_session_count": len(history),
        "volume_pace_ratio": str(volume_pace_ratio) if volume_pace_ratio is not None else None,
    }


def check(symbols=DEFAULT_SYMBOLS, now=None, fetcher=get_json):
    symbols = normalize_symbols(symbols)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    output = {
        "checked_at": now.isoformat(),
        "provider": "yahoo_finance_public_chart",
        "base_url": BASE_URL,
        "credentials_required": False,
        "interval": INTERVAL,
        "range": RANGE,
        "requested_symbols": symbols,
        "verified_symbols": [],
        "price_bars_verified": False,
        "session_volume_verified": False,
        "derived_vwap_verified": False,
        "recent_daily_volume_verified": False,
        "freshness_verified": False,
        "market_data_ready": False,
        "limitations": [
            "Public undocumented endpoint; availability and fields may change without notice",
            "Bars are research evidence only and are not described as consolidated SIP data",
            "Derived VWAP uses 5-minute typical prices and is not an official exchange VWAP",
            "Binance remains the source for the simulated executable bid and ask",
        ],
        "errors": [],
        "symbols": {},
    }
    for symbol in symbols:
        data, error = fetcher(symbol)
        if error:
            output["errors"].append(symbol + ": " + error)
            continue
        summary = summarize_symbol(data, now)
        if summary is None:
            output["errors"].append(symbol + ": unexpected chart response")
            continue
        output["symbols"][symbol] = summary
        if all(summary.get(key) for key in (
            "fresh", "price_bar_ok", "session_volume_ok", "derived_vwap_ok", "history_ok"
        )):
            output["verified_symbols"].append(symbol)
    output["price_bars_verified"] = all(output["symbols"].get(symbol, {}).get("price_bar_ok") for symbol in symbols)
    output["session_volume_verified"] = all(output["symbols"].get(symbol, {}).get("session_volume_ok") for symbol in symbols)
    output["derived_vwap_verified"] = all(output["symbols"].get(symbol, {}).get("derived_vwap_ok") for symbol in symbols)
    output["recent_daily_volume_verified"] = all(output["symbols"].get(symbol, {}).get("history_ok") for symbol in symbols)
    output["freshness_verified"] = all(output["symbols"].get(symbol, {}).get("fresh") for symbol in symbols)
    output["market_data_ready"] = len(output["verified_symbols"]) == len(symbols)
    if not output["market_data_ready"]:
        missing = [symbol for symbol in symbols if symbol not in output["verified_symbols"]]
        output["errors"].append("Not ready for new paper positions: " + ",".join(missing))
    return output


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
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--update-readiness", action="store_true")
    args = parser.parse_args()
    try:
        result = check(args.symbols)
        if args.update_readiness:
            update_readiness(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["market_data_ready"]:
            return 0
        return 3 if any("Network" in error for error in result["errors"]) else 2
    except (OSError, ValueError):
        print(json.dumps({"error": "Public market-data check failed; no paper position is allowed"}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
