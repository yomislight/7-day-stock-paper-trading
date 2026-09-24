#!/usr/bin/env python3
"""Read-only Binance Stocks checks. No orders, transfers or account agreements."""

import argparse
import hashlib
import hmac
import json
import os
import tempfile
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "10-API密钥-仅本地-local-secrets" / "binance-api.env"
HOSTS = {
    "production": "https://api.binance.com",
    "testnet": "https://testnet.binance.vision",
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_config(path):
    values = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or key not in {"BINANCE_API_KEY", "BINANCE_API_SECRET", "BINANCE_ENV"} or key in values:
            raise ValueError("Invalid or duplicate setting at line %d" % number)
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Unclosed quote at line %d" % number)
            value = value[1:-1]
        if any(char.isspace() for char in value) or not value.isascii():
            raise ValueError("Invalid setting format at line %d" % number)
        values[key] = value
    if values.get("BINANCE_ENV") not in HOSTS:
        raise ValueError("BINANCE_ENV must be production or testnet")
    return values


def get_json(url, headers=None):
    # Fixed official hosts and no redirects prevent credential forwarding.
    req = Request(url, headers={"User-Agent": "binance-spot/1.0.1 (Skill)", **(headers or {})}, method="GET")
    try:
        with build_opener(NoRedirect()).open(req, timeout=10) as response:
            body = response.read()
            if not body:
                return None, "No data available"
            data = json.loads(body)
        if not isinstance(data, (dict, list)):
            return None, "Unexpected response shape"
        return data, None
    except HTTPError as exc:
        # Only a numeric API error code is safe to export, never raw server text.
        suffix = ""
        try:
            body = json.loads(exc.read())
            code = body.get("code") if isinstance(body, dict) else None
            if type(code) is int:
                suffix = " / Binance %d" % code
        except (OSError, ValueError, UnicodeError):
            pass
        return None, "HTTP %d%s" % (exc.code, suffix)
    except (URLError, TimeoutError, OSError):
        return None, "Network or TLS error"
    except (ValueError, UnicodeError):
        return None, "Invalid JSON response"


def check(config, public_only=False):
    env = config["BINANCE_ENV"]
    base = HOSTS[env]
    key = config.get("BINANCE_API_KEY", "")
    secret = config.get("BINANCE_API_SECRET", "")
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "environment": env,
        "credentials_present": bool(key and secret),
        "public_api_reachable": False,
        "signed_account_read_verified": False,
        "api_key_permissions_verified": False,
        "stock_etf_access_verified": False,
        "orders_allowed": False,
        "errors": [],
    }
    ping, error = get_json(base + "/api/v3/ping")
    if error:
        result["errors"].append("ping: " + error)
    server, error = get_json(base + "/api/v3/time")
    stamp = server.get("serverTime") if isinstance(server, dict) else None
    time_valid = type(stamp) is int and stamp > 0
    if error or not time_valid:
        result["errors"].append("time: " + (error or "Missing serverTime"))
    result["public_api_reachable"] = ping == {} and time_valid
    if not public_only:
        if not key or not secret:
            result["errors"].append("Fill both credentials in 10-API密钥-仅本地-local-secrets/binance-api.env locally")
        elif result["public_api_reachable"]:
            query = urlencode({"timestamp": stamp, "recvWindow": 5000})
            signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
            account, error = get_json(
                base + "/api/v3/account?" + query + "&signature=" + signature,
                {"X-MBX-APIKEY": key},
            )
            verified = (isinstance(account, dict)
                        and type(account.get("canTrade")) is bool
                        and isinstance(account.get("balances"), list))
            result["signed_account_read_verified"] = verified
            if not verified:
                result["errors"].append("account: " + (error or "Unexpected account response"))
    return result


def signed_get(config, path):
    server, error = get_json(HOSTS["production"] + "/api/v3/time")
    stamp = server.get("serverTime") if isinstance(server, dict) else None
    if error or type(stamp) is not int or stamp <= 0:
        return None, "Server time unavailable"
    query = urlencode({"timestamp": stamp, "recvWindow": 5000})
    signature = hmac.new(config["BINANCE_API_SECRET"].encode(), query.encode(), hashlib.sha256).hexdigest()
    return get_json(HOSTS["production"] + path + "?" + query + "&signature=" + signature,
                    {"X-MBX-APIKEY": config["BINANCE_API_KEY"]})


def valid_quote(quote, symbol):
    if not isinstance(quote, dict) or quote.get("symbol") != symbol:
        return False
    try:
        bid, ask = Decimal(str(quote["bidPrice"])), Decimal(str(quote["askPrice"]))
        return bid.is_finite() and ask.is_finite() and 0 < bid <= ask
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return False


def check_stocks(config, public_only=False, symbol="AAPL"):
    result = check(config, public_only=public_only)
    result.update({"scope": "stocks", "stock_rules_read_verified": False,
                   "stock_quote_read_verified": False, "stock_orders_read_verified": False,
                   "quote_freshness_verified": False, "stock_symbol": symbol})
    if public_only:
        return result
    if config["BINANCE_ENV"] != "production":
        result["errors"].append("Stocks sandbox is not verified; Spot testnet cannot verify Stocks")
        return result
    if not result["credentials_present"] or not result["public_api_reachable"]:
        return result
    headers = {"X-MBX-APIKEY": config["BINANCE_API_KEY"]}
    rules, error = get_json(HOSTS["production"] + "/sapi/v1/equity/market/exchangeInfo?" + urlencode({"symbol": symbol}), headers)
    symbols = rules.get("symbols") if isinstance(rules, dict) else None
    matches = [s for s in symbols if isinstance(s, dict) and s.get("symbol") == symbol] if isinstance(symbols, list) else []
    result["stock_rules_read_verified"] = bool(matches)
    if not matches:
        result["errors"].append("stock_rules: " + (error or "No matching equity symbol"))
    else:
        fields = ("symbol", "tradability", "fractionable", "fractionableEh", "stepSize", "minQty", "minNotional", "maxNotional")
        result["stock_rules"] = {k: matches[0].get(k) for k in fields}
    quote, error = get_json(HOSTS["production"] + "/sapi/v1/equity/market/quote?" + urlencode({"symbol": symbol}), headers)
    result["stock_quote_read_verified"] = valid_quote(quote, symbol)
    if result["stock_quote_read_verified"]:
        result["quote"] = {k: quote[k] for k in ("symbol", "bidPrice", "askPrice")}
        result["quote_received_at"] = datetime.now(timezone.utc).isoformat()
        # Binance documents this latest quote as at most about five seconds stale.
        result["quote_freshness_verified"] = True
    else:
        result["errors"].append("stock_quote: " + (error or "Invalid quote"))
    orders, error = signed_get(config, "/sapi/v1/equity/order/open-orders")
    result["stock_orders_read_verified"] = isinstance(orders, list) and all(
        isinstance(order, dict) and isinstance(order.get("orderId"), str) for order in orders)
    if not result["stock_orders_read_verified"]:
        result["errors"].append("stock_orders: " + (error or "Unexpected response"))
    permissions, error = signed_get(config, "/sapi/v1/account/apiRestrictions")
    result["api_key_permissions_verified"] = isinstance(permissions, dict) and type(permissions.get("enableReading")) is bool
    if result["api_key_permissions_verified"]:
        result["key_permissions"] = {k: v for k, v in permissions.items()
                                     if k in {"enableReading", "enableWithdrawals", "enableSpotAndMarginTrading", "ipRestrict"} and type(v) is bool}
    else:
        result["errors"].append("api_permissions: " + (error or "Unexpected response"))
    result["stock_etf_access_verified"] = all(result[k] for k in (
        "stock_rules_read_verified", "stock_quote_read_verified", "stock_orders_read_verified"))
    return result


def update_readiness(result):
    path = ROOT / "04-运行状态-state" / "readiness.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("Invalid readiness state")
    # A Spot check does not refresh unrelated stock/ETF readiness or its timestamp.
    state["binance_stocks_api" if result.get("scope") == "stocks" else "binance_spot_api"] = result
    if result.get("scope") == "stocks":
        state["binance_stock_api_read_access_verified"] = result.get("stock_etf_access_verified", False)
        state["last_readiness_check"] = result.get("checked_at")
    state["orders_allowed"] = False
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
    parser.add_argument("--public-only", action="store_true", help="Skip signed account reads")
    parser.add_argument("--check-config", action="store_true", help="Validate locally without network")
    parser.add_argument("--update-readiness", action="store_true")
    parser.add_argument("--spot-only", action="store_true", help="Only diagnose the Spot account")
    args = parser.parse_args()
    try:
        config = load_config(CONFIG)
        if args.check_config:
            present = bool(config.get("BINANCE_API_KEY") and config.get("BINANCE_API_SECRET"))
            print(json.dumps({"config_valid": True, "credentials_present": present}))
            return 0 if present else 2
        result = (check if args.spot_only else check_stocks)(config, public_only=args.public_only)
        if args.update_readiness:
            update_readiness(result)
        print(json.dumps(result, indent=2))
        if not result["public_api_reachable"]:
            return 3
        passed = result["signed_account_read_verified"] if args.spot_only else result["stock_etf_access_verified"]
        return 0 if args.public_only or passed else 2
    except (OSError, ValueError):
        print(json.dumps({"error": "Check local config/state file existence and format; details suppressed to protect credentials"}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
