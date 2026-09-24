#!/usr/bin/env python3
"""Execute one autonomous local paper-trading decision; never sends a broker order."""

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from binance_readiness_check import HOSTS, check_stocks, get_json, load_config, update_readiness
from daily_report import write_daily_report
from paper_ledger import PaperLedger, PaperLedgerError, atomic_json, decimal_value
from public_market_data_check import check as check_market_data, update_readiness as update_market_data_readiness

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "10-API密钥-仅本地-local-secrets" / "binance-api.env"


class PaperEngineError(ValueError):
    pass


def build_ledger():
    return PaperLedger(
        ROOT / "05-交易记录-data" / "current-state.json",
        ROOT / "04-运行状态-state" / "readiness.json",
        ROOT / "04-运行状态-state" / "paper-config.json",
        ROOT / "05-交易记录-data" / "paper-ledger.json",
    )


def load_decision(path):
    decision = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(decision, dict):
        raise PaperEngineError("Decision must be a JSON object")
    if decision.get("paper_trading_only") is not True:
        raise PaperEngineError("Decision must explicitly confirm paper_trading_only")
    action = decision.get("action")
    if action not in {"open_long", "manage", "close", "no_trade"}:
        raise PaperEngineError("Unsupported paper decision action")
    return decision


def fetch_snapshot(config, symbol, now):
    """Read current ordinary-equity rules and quote using GET-only endpoints."""
    symbol = str(symbol).upper()
    headers = {"X-MBX-APIKEY": config["BINANCE_API_KEY"]}
    base = HOSTS["production"]
    rules_data, error = get_json(base + "/sapi/v1/equity/market/exchangeInfo?symbol=" + symbol, headers)
    symbols = rules_data.get("symbols") if isinstance(rules_data, dict) else None
    matches = [item for item in symbols if isinstance(item, dict) and item.get("symbol") == symbol] if isinstance(symbols, list) else []
    if not matches:
        raise PaperEngineError("No tradable paper rules for the selected symbol")
    quote_data, error = get_json(base + "/sapi/v1/equity/market/quote?symbol=" + symbol, headers)
    if not isinstance(quote_data, dict) or quote_data.get("symbol") != symbol:
        raise PaperEngineError("No current paper quote for the selected symbol")
    try:
        bid = decimal_value(quote_data["bidPrice"], "bidPrice")
        ask = decimal_value(quote_data["askPrice"], "askPrice")
        bid_size = decimal_value(quote_data["bidSize"], "bidSize")
        ask_size = decimal_value(quote_data["askSize"], "askSize")
    except (KeyError, PaperLedgerError) as exc:
        raise PaperEngineError("Invalid paper quote shape") from exc
    if not (0 < bid <= ask and bid_size > 0 and ask_size > 0):
        raise PaperEngineError("Paper quote is not executable")
    rule = matches[0]
    return {
        "rules": {key: rule.get(key) for key in (
            "symbol", "tradability", "fractionable", "stepSize", "minQty", "maxQty", "minNotional", "maxNotional")},
        "quote": {
            "symbol": symbol,
            "bid": str(bid),
            "ask": str(ask),
            "bid_size": str(bid_size),
            "ask_size": str(ask_size),
            "received_at": now.isoformat(),
        },
    }


def prior_event(ledger, run_id):
    return next((event for event in ledger.ledger.get("events", []) if event.get("run_id") == run_id), None)


def decision_symbol(decision, ledger):
    if decision["action"] == "open_long":
        return str(decision.get("symbol", "")).upper()
    positions = ledger.state.get("positions", [])
    if positions:
        return positions[0]["symbol"]
    return str(decision.get("symbol", "AAPL")).upper()


def execute(decision, run_id, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    ledger = build_ledger()
    duplicate = prior_event(ledger, run_id)
    if duplicate:
        return {"status": "duplicate_skipped", "event": duplicate, "snapshot": None}

    symbol = decision_symbol(decision, ledger)
    if not symbol:
        raise PaperEngineError("A symbol is required")
    config = load_config(CONFIG)
    readiness = check_stocks(config, symbol=symbol)
    update_readiness(readiness)
    if readiness.get("stock_etf_access_verified") is not True:
        raise PaperEngineError("Fresh Stocks read verification failed")
    if decision["action"] == "open_long":
        try:
            market_data = check_market_data([symbol], now=now)
        except (OSError, ValueError) as exc:
            raise PaperEngineError("Public supplemental market data is not ready") from exc
        update_market_data_readiness(market_data)
        if market_data.get("market_data_ready") is not True or symbol not in market_data.get("verified_symbols", []):
            raise PaperEngineError("Fresh public 5-minute volume and derived VWAP are required for a new paper position")

    # The API check itself takes time; use a post-refresh timestamp for freshness validation.
    now = datetime.now(timezone.utc)
    ledger = build_ledger()
    ledger.validate_readiness(now)
    snapshot = fetch_snapshot(config, symbol, now)
    if decision["action"] == "open_long":
        snapshot["supplemental_market_data"] = {
            "provider": market_data.get("provider"),
            "limitations": market_data.get("limitations", []),
            "symbol": market_data.get("symbols", {}).get(symbol),
        }
    action = decision["action"]
    if action == "no_trade":
        return {"status": "no_trade", "event": None, "snapshot": snapshot}
    if action == "open_long":
        request = {
            "run_id": run_id,
            "symbol": symbol,
            "quote": snapshot["quote"],
            "rules": snapshot["rules"],
            "stop_price": decision.get("stop_price"),
            "target_price": decision.get("target_price"),
            "thesis": decision.get("thesis", ""),
            "evidence": decision.get("evidence"),
        }
        event = ledger.open_long(request, now)
    elif action == "manage":
        event = ledger.mark({"run_id": run_id, "quote": snapshot["quote"]}, now, evaluate=True)
    else:
        event = ledger.close({"run_id": run_id, "quote": snapshot["quote"],
                              "reason": decision.get("reason", "end_of_day")}, now)
    return {"status": "executed", "event": event, "snapshot": snapshot}


def write_records(run_id, decision, result, now):
    ledger = build_ledger()
    local = now.astimezone(ZoneInfo("America/Chicago"))
    state = ledger.state
    local_date = local.date().isoformat()
    if state.get("risk_date") != local_date:
        state["risk_date"] = local_date
        state["daily_realized_pnl_usdt"] = 0
        if not state.get("positions"):
            state["daily_open_risk_usdt"] = 0
    dates = state.get("planned_trading_dates", [])
    if local_date in dates:
        state["trading_day_index"] = dates.index(local_date) + 1
    state["last_run"] = {
        "run_id": run_id,
        "timestamp": now.isoformat(),
        "mode": "autonomous_local_paper",
        "stock_api_verified": True,
        "orders_placed": False,
        "paper_action": decision["action"],
        "paper_result": result["status"],
    }
    state["next_task_focus"] = "下一次定时检查时更新市场证据，并重新评估模拟持仓或空仓状态；真实交易继续禁用。"
    atomic_json(ROOT / "05-交易记录-data" / "current-state.json", state)
    evidence = {
        "run_id": run_id,
        "timestamp": now.isoformat(),
        "mode": "local_paper_only",
        "live_order_sent": False,
        "decision": decision,
        "result": result,
        "state": {key: state.get(key) for key in ("cash_usdt", "equity_usdt", "positions", "daily_open_risk_usdt")},
    }
    atomic_json(ROOT / "05-交易记录-data" / "证据资料-evidence" / (run_id + ".json"), evidence)
    journal_path = ROOT / "05-交易记录-data" / "运行日志-journal" / (local_date + ".md")
    action = decision["action"]
    event = result.get("event") or {}
    action_zh = {"open_long": "模拟买入", "manage": "持仓管理", "close": "模拟卖出", "no_trade": "不交易"}[action]
    lines = [
        "", "## 自动模拟交易：" + run_id + " - " + now.isoformat(), "",
        "- 本次做了什么：处理了一次本地模拟交易决策，结果为“" + action_zh + "”。",
        "- 为什么这么做：用户已授权系统在书面风险限制内自主进行模拟交易判断。",
        "- 是否提出订单：" + ("是，仅模拟买入" if action == "open_long" else "否") + "。",
        "- 是否真实下单：否，只写入本地模拟账本。",
        "- 是否成交：" + ("是，本地模拟成交" if event else "否") + "。",
        "- 当前持仓：" + json.dumps(state.get("positions", []), ensure_ascii=False) + "。",
        "- 当前模拟现金：" + str(state.get("cash_usdt")) + " USDT。",
        "- 当前未平仓风险：" + str(state.get("daily_open_risk_usdt")) + " USDT。",
        "- 证据文件：`05-交易记录-data/证据资料-evidence/" + run_id + ".json`。",
        "- 下一次重点：刷新只读行情，重新评估模拟持仓或空仓状态。",
        "- 需要人工确认：模拟交易不需要；真实交易继续禁用。",
    ]
    with journal_path.open("a", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")
    write_daily_report(local_date, ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", required=True, type=Path, help="Non-secret JSON paper decision")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    try:
        decision = load_decision(args.decision)
        result = execute(decision, args.run_id, now)
        write_records(args.run_id, decision, result, now)
        print(json.dumps({"paper_trading": True, "live_order_sent": False, **result}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, PaperLedgerError, PaperEngineError) as exc:
        print(json.dumps({"paper_trading": True, "live_order_sent": False,
                          "error": "Paper decision rejected; no broker order was sent.",
                          "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
