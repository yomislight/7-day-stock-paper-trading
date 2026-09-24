#!/usr/bin/env python3
"""Deterministic local paper ledger. This module has no broker write path."""

import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from zoneinfo import ZoneInfo


class PaperLedgerError(ValueError):
    pass


def decimal_value(value, name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise PaperLedgerError("Invalid decimal: " + name) from None
    if not result.is_finite():
        raise PaperLedgerError("Non-finite decimal: " + name)
    return result


def json_number(value):
    rounded = value.quantize(Decimal("0.00000001"))
    return int(rounded) if rounded == rounded.to_integral() else float(rounded)


def floor_step(value, step):
    if step <= 0:
        raise PaperLedgerError("stepSize must be positive")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def parse_time(value, name):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise PaperLedgerError("Invalid timestamp: " + name) from None
    if parsed.tzinfo is None:
        raise PaperLedgerError("Timestamp must include timezone: " + name)
    return parsed.astimezone(timezone.utc)


def atomic_json(path, payload):
    temporary = None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class PaperLedger:
    def __init__(self, state_path, readiness_path, config_path, ledger_path):
        self.state_path = Path(state_path)
        self.readiness_path = Path(readiness_path)
        self.config_path = Path(config_path)
        self.ledger_path = Path(ledger_path)
        self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.readiness = json.loads(self.readiness_path.read_text(encoding="utf-8"))
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def validate_readiness(self, now=None):
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        required = {
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "broker_connected": True,
            "human_confirmation_required_for_live_orders": True,
            "binance_stock_trading_eligibility_verified": True,
            "binance_stock_api_read_access_verified": True,
            "local_paper_ledger_initialized": True,
            "autonomous_paper_execution_enabled": True,
            "orders_allowed": False,
        }
        for key, expected in required.items():
            if self.readiness.get(key) is not expected:
                raise PaperLedgerError("Unsafe or missing readiness field: " + key)
        check = self.readiness.get("binance_stocks_api")
        if not isinstance(check, dict) or check.get("stock_etf_access_verified") is not True:
            raise PaperLedgerError("Fresh Binance Stocks read verification is required")
        checked_at = parse_time(check.get("checked_at"), "readiness.checked_at")
        max_age = decimal_value(self.config["readiness_max_age_hours"], "readiness_max_age_hours")
        age_hours = Decimal(str((now - checked_at).total_seconds())) / Decimal("3600")
        if age_hours < 0 or age_hours > max_age:
            raise PaperLedgerError("Binance Stocks readiness is stale")
        for key in ("max_position_size_percent", "max_daily_loss_percent", "max_single_trade_loss_percent"):
            if key not in self.readiness:
                raise PaperLedgerError("Missing risk limit: " + key)

    def _limits(self):
        capital = decimal_value(self.state["starting_capital_usdt"], "starting_capital_usdt")
        return {
            "capital": capital,
            "position": capital * decimal_value(self.readiness["max_position_size_percent"], "position percent") / 100,
            "daily": capital * decimal_value(self.readiness["max_daily_loss_percent"], "daily percent") / 100,
            "trade": capital * decimal_value(self.readiness["max_single_trade_loss_percent"], "trade percent") / 100,
        }

    def _roll_trading_day(self, now):
        local_date = now.astimezone(ZoneInfo("America/Chicago")).date().isoformat()
        if self.state.get("risk_date") != local_date:
            self.state["risk_date"] = local_date
            self.state["daily_realized_pnl_usdt"] = 0
            if not self.state.get("positions"):
                self.state["daily_open_risk_usdt"] = 0
        dates = self.state.get("planned_trading_dates", [])
        if local_date in dates:
            self.state["trading_day_index"] = dates.index(local_date) + 1
        return local_date

    def _assert_entry_window(self, now):
        local = now.astimezone(ZoneInfo("America/Chicago"))
        if local.date().isoformat() not in self.state.get("planned_trading_dates", []):
            raise PaperLedgerError("Not a planned trading date")
        open_hour, open_minute = map(int, self.config["regular_session_open_ct"].split(":"))
        cut_hour, cut_minute = map(int, self.config["new_entry_cutoff_ct"].split(":"))
        minute = local.hour * 60 + local.minute
        if not (open_hour * 60 + open_minute <= minute <= cut_hour * 60 + cut_minute):
            raise PaperLedgerError("New paper entries are outside the allowed window")

    def _validate_quote(self, symbol, quote, now, side):
        if not isinstance(quote, dict) or str(quote.get("symbol", "")).upper() != symbol:
            raise PaperLedgerError("Quote symbol mismatch")
        bid = decimal_value(quote.get("bid"), "bid")
        ask = decimal_value(quote.get("ask"), "ask")
        bid_size = decimal_value(quote.get("bid_size"), "bid_size")
        ask_size = decimal_value(quote.get("ask_size"), "ask_size")
        if not (0 < bid <= ask and bid_size > 0 and ask_size > 0):
            raise PaperLedgerError("Quote is not executable")
        mid = (bid + ask) / 2
        spread_bps = (ask - bid) / mid * 10000
        if spread_bps > decimal_value(self.config["max_spread_bps"], "max_spread_bps"):
            raise PaperLedgerError("Spread exceeds paper limit")
        received_at = parse_time(quote.get("received_at"), "quote.received_at")
        age = Decimal(str((now - received_at).total_seconds()))
        if age < Decimal("-2") or age > decimal_value(self.config["quote_max_age_seconds"], "quote_max_age_seconds"):
            raise PaperLedgerError("Quote is stale")
        return {
            "bid": bid,
            "ask": ask,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "received_at": received_at.isoformat(),
            "executable_size": ask_size if side == "buy" else bid_size,
            "spread_bps": spread_bps,
        }

    def _validate_evidence(self, evidence):
        if not isinstance(evidence, list):
            raise PaperLedgerError("Evidence must be a list")
        categories = set()
        for item in evidence:
            if not isinstance(item, dict) or not item.get("category") or not item.get("source"):
                raise PaperLedgerError("Each evidence item needs category and source")
            categories.add(str(item["category"]).strip().lower())
        if len(categories) < int(self.config["minimum_evidence_categories"]):
            raise PaperLedgerError("At least two independent evidence categories are required")

    def _validate_rules(self, symbol, rules, side):
        if not isinstance(rules, dict) or str(rules.get("symbol", "")).upper() != symbol:
            raise PaperLedgerError("Trading rules symbol mismatch")
        allowed = {"BUY_SELL", "BUY"} if side == "buy" else {"BUY_SELL", "SELL"}
        if rules.get("tradability") not in allowed:
            raise PaperLedgerError("Symbol is not tradable for requested side")
        if side == "buy" and rules.get("fractionable") is not True:
            raise PaperLedgerError("Regular-session fractional trading is required")
        return {
            "step": decimal_value(rules.get("stepSize"), "stepSize"),
            "min_qty": decimal_value(rules.get("minQty") or "0", "minQty"),
            "max_qty": decimal_value(rules.get("maxQty") or "1E18", "maxQty"),
            "min_notional": decimal_value(rules.get("minNotional") or "0", "minNotional"),
            "max_notional": decimal_value(rules.get("maxNotional") or "1E18", "maxNotional"),
        }

    def _cost_rates(self):
        return (
            decimal_value(self.config["fee_bps_per_side"], "fee_bps_per_side") / 10000,
            decimal_value(self.config["slippage_bps_per_side"], "slippage_bps_per_side") / 10000,
        )

    def _next_id(self, now):
        sequence = int(self.ledger.get("next_sequence", 1))
        self.ledger["next_sequence"] = sequence + 1
        return "PAPER-%s-%04d" % (now.astimezone(ZoneInfo("America/Chicago")).strftime("%Y%m%d"), sequence)

    def _portfolio_values(self, position=None, bid=None):
        cash = decimal_value(self.state["cash_usdt"], "cash_usdt")
        if position is None:
            return cash, Decimal("0"), Decimal("0")
        quantity = decimal_value(position["quantity"], "position.quantity")
        mark = bid if bid is not None else decimal_value(position["mark_price"], "mark_price")
        fee_rate, _ = self._cost_rates()
        exit_fee = quantity * mark * fee_rate
        liquidation = quantity * mark - exit_fee
        cost_basis = decimal_value(position["cost_basis_usdt"], "cost_basis_usdt")
        return cash + liquidation, liquidation - cost_basis, exit_fee

    def _save_event(self, event):
        event["state_after"] = copy.deepcopy(self.state)
        self.ledger.setdefault("events", []).append(event)
        atomic_json(self.ledger_path, self.ledger)
        atomic_json(self.state_path, self.state)

    def open_long(self, request, now=None):
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.validate_readiness(now)
        self._roll_trading_day(now)
        self._assert_entry_window(now)
        if self.state.get("positions"):
            raise PaperLedgerError("Only one active paper position is allowed")
        symbol = str(request.get("symbol", "")).upper()
        if symbol not in self.state.get("watchlist", []):
            raise PaperLedgerError("Symbol is outside the approved watchlist")
        self._validate_evidence(request.get("evidence"))
        quote = self._validate_quote(symbol, request.get("quote"), now, "buy")
        rules = self._validate_rules(symbol, request.get("rules"), "buy")
        stop = decimal_value(request.get("stop_price"), "stop_price")
        target = decimal_value(request.get("target_price"), "target_price")
        fee_rate, slip_rate = self._cost_rates()
        entry = quote["ask"] * (1 + slip_rate)
        stop_fill = stop * (1 - slip_rate)
        target_fill = target * (1 - slip_rate)
        if not (0 < stop < entry < target):
            raise PaperLedgerError("Require stop < entry < target")
        loss_per_share = entry - stop_fill + entry * fee_rate + stop_fill * fee_rate
        reward_per_share = target_fill - entry - entry * fee_rate - target_fill * fee_rate
        if loss_per_share <= 0 or reward_per_share / loss_per_share < decimal_value(
                self.config["minimum_reward_risk"], "minimum_reward_risk"):
            raise PaperLedgerError("Net reward/risk is below the configured minimum")
        limits = self._limits()
        cash = decimal_value(self.state["cash_usdt"], "cash_usdt")
        daily_loss = max(Decimal("0"), -decimal_value(self.state.get("daily_realized_pnl_usdt", 0), "daily pnl"))
        remaining_daily = limits["daily"] - daily_loss
        if remaining_daily <= 0:
            raise PaperLedgerError("Daily loss limit has been reached")
        quantity = min(
            limits["position"] / entry,
            limits["trade"] / loss_per_share,
            remaining_daily / loss_per_share,
            cash / (entry * (1 + fee_rate)),
            quote["executable_size"],
            rules["max_qty"],
            rules["max_notional"] / entry,
        )
        quantity = floor_step(quantity, rules["step"])
        notional = quantity * entry
        entry_fee = notional * fee_rate
        planned_loss = quantity * loss_per_share
        if quantity <= 0 or quantity < rules["min_qty"] or notional < rules["min_notional"]:
            raise PaperLedgerError("Rounded paper quantity does not meet exchange limits")
        if notional > limits["position"] or planned_loss > limits["trade"]:
            raise PaperLedgerError("Paper order exceeds a risk limit")
        if notional + entry_fee > cash:
            raise PaperLedgerError("Insufficient paper cash")
        local_date = now.astimezone(ZoneInfo("America/Chicago")).date().isoformat()
        recent_closes = [event for event in self.ledger.get("events", [])
                         if event.get("action") == "close" and event.get("trading_date") == local_date]
        if len(recent_closes) >= 2 and all(event.get("reason") == "stop" for event in recent_closes[-2:]):
            raise PaperLedgerError("Two consecutive stops block new entries")
        order_id = self._next_id(now)
        position = {
            "symbol": symbol,
            "side": "long",
            "quantity": str(quantity),
            "entry_price": str(entry),
            "mark_price": str(quote["bid"]),
            "stop_price": str(stop),
            "target_price": str(target),
            "entry_time": now.isoformat(),
            "cost_basis_usdt": str(notional + entry_fee),
            "entry_fee_usdt": str(entry_fee),
            "planned_loss_usdt": str(planned_loss),
            "thesis": str(request.get("thesis", "")).strip(),
            "evidence": copy.deepcopy(request["evidence"]),
            "order_id": order_id,
        }
        self.state["cash_usdt"] = json_number(cash - notional - entry_fee)
        self.state["positions"] = [position]
        self.state["open_orders"] = []
        equity, unrealized, _ = self._portfolio_values(position, quote["bid"])
        self.state["equity_usdt"] = json_number(equity)
        self.state["unrealized_pnl_usdt"] = json_number(unrealized)
        self.state["daily_open_risk_usdt"] = json_number(planned_loss)
        self.state["paper_fees_paid_usdt"] = json_number(
            decimal_value(self.state.get("paper_fees_paid_usdt", 0), "fees") + entry_fee)
        event = {
            "event_id": order_id + "-OPEN",
            "order_id": order_id,
            "action": "open_long",
            "trading_date": local_date,
            "timestamp": now.isoformat(),
            "symbol": symbol,
            "quantity": str(quantity),
            "fill_price": str(entry),
            "fee_usdt": str(entry_fee),
            "planned_loss_usdt": str(planned_loss),
            "quote": request["quote"],
            "reason": "strategy_entry",
        }
        if request.get("run_id"):
            event["run_id"] = str(request["run_id"])
        self._save_event(event)
        return event

    def mark(self, request, now=None, evaluate=False):
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.validate_readiness(now)
        self._roll_trading_day(now)
        positions = self.state.get("positions", [])
        if len(positions) != 1:
            raise PaperLedgerError("Exactly one active paper position is required")
        position = positions[0]
        symbol = position["symbol"]
        quote = self._validate_quote(symbol, request.get("quote"), now, "sell")
        position["mark_price"] = str(quote["bid"])
        quantity = decimal_value(position["quantity"], "quantity")
        stop = decimal_value(position["stop_price"], "stop")
        fee_rate, slip_rate = self._cost_rates()
        stop_exit = stop * (1 - slip_rate)
        stop_fee = quantity * stop_exit * fee_rate
        cost_basis = decimal_value(position["cost_basis_usdt"], "cost_basis")
        open_risk = max(Decimal("0"), cost_basis - (quantity * stop_exit - stop_fee))
        equity, unrealized, _ = self._portfolio_values(position, quote["bid"])
        self.state["equity_usdt"] = json_number(equity)
        self.state["unrealized_pnl_usdt"] = json_number(unrealized)
        self.state["daily_open_risk_usdt"] = json_number(open_risk)
        if evaluate and quote["bid"] <= stop:
            return self.close({"quote": request["quote"], "reason": "stop", "run_id": request.get("run_id")}, now)
        if evaluate and quote["bid"] >= decimal_value(position["target_price"], "target"):
            return self.close({"quote": request["quote"], "reason": "target", "run_id": request.get("run_id")}, now)
        event = {
            "event_id": self._next_id(now) + "-MARK",
            "action": "mark",
            "trading_date": now.astimezone(ZoneInfo("America/Chicago")).date().isoformat(),
            "timestamp": now.isoformat(),
            "symbol": symbol,
            "mark_price": str(quote["bid"]),
            "quote": request["quote"],
            "reason": "risk_refresh",
        }
        if request.get("run_id"):
            event["run_id"] = str(request["run_id"])
        self._save_event(event)
        return event

    def close(self, request, now=None):
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.validate_readiness(now)
        self._roll_trading_day(now)
        positions = self.state.get("positions", [])
        if len(positions) != 1:
            raise PaperLedgerError("Exactly one active paper position is required")
        position = positions[0]
        symbol = position["symbol"]
        quote = self._validate_quote(symbol, request.get("quote"), now, "sell")
        quantity = decimal_value(position["quantity"], "quantity")
        fee_rate, slip_rate = self._cost_rates()
        fill = quote["bid"] * (1 - slip_rate)
        if quote["executable_size"] < quantity:
            raise PaperLedgerError("Quoted bid size cannot support the paper exit")
        proceeds = quantity * fill
        exit_fee = proceeds * fee_rate
        cost_basis = decimal_value(position["cost_basis_usdt"], "cost_basis")
        net_pnl = proceeds - exit_fee - cost_basis
        cash = decimal_value(self.state["cash_usdt"], "cash") + proceeds - exit_fee
        self.state["cash_usdt"] = json_number(cash)
        self.state["equity_usdt"] = json_number(cash)
        self.state["realized_pnl_usdt"] = json_number(
            decimal_value(self.state.get("realized_pnl_usdt", 0), "realized pnl") + net_pnl)
        self.state["daily_realized_pnl_usdt"] = json_number(
            decimal_value(self.state.get("daily_realized_pnl_usdt", 0), "daily pnl") + net_pnl)
        self.state["unrealized_pnl_usdt"] = 0
        self.state["daily_open_risk_usdt"] = 0
        self.state["positions"] = []
        self.state["open_orders"] = []
        self.state["paper_fees_paid_usdt"] = json_number(
            decimal_value(self.state.get("paper_fees_paid_usdt", 0), "fees") + exit_fee)
        reason = str(request.get("reason", "manual_exit"))
        if reason not in {"stop", "target", "thesis_invalid", "time_exit", "end_of_day", "manual_exit"}:
            raise PaperLedgerError("Unsupported paper exit reason")
        order_id = self._next_id(now)
        event = {
            "event_id": order_id + "-CLOSE",
            "order_id": order_id,
            "action": "close",
            "trading_date": now.astimezone(ZoneInfo("America/Chicago")).date().isoformat(),
            "timestamp": now.isoformat(),
            "symbol": symbol,
            "quantity": str(quantity),
            "fill_price": str(fill),
            "fee_usdt": str(exit_fee),
            "net_pnl_usdt": str(net_pnl),
            "quote": request["quote"],
            "reason": reason,
        }
        if request.get("run_id"):
            event["run_id"] = str(request["run_id"])
        self._save_event(event)
        return event

    def reconcile(self):
        events = self.ledger.get("events", [])
        if not events or "state_after" not in events[-1]:
            raise PaperLedgerError("No paper event snapshot is available for reconciliation")
        self.state = copy.deepcopy(events[-1]["state_after"])
        atomic_json(self.state_path, self.state)
        return self.state
