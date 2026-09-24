#!/usr/bin/env python3
"""Six-slot, read-only runner with locking, duplicate prevention and export recovery."""

import argparse
import fcntl
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from binance_readiness_check import CONFIG, ROOT, check_stocks, load_config, update_readiness
from daily_report import write_daily_report
from public_market_data_check import check as check_market_data, update_readiness as update_market_data_readiness
from run_store import RunStore, utc_now

STARTUP = ("AGENTS.md", "AGENTS.zh-CN.md", "02-项目文档-docs/TRADING-STRATEGY.md", "02-项目文档-docs/TRADING-STRATEGY.zh-CN.md",
           "03-定时任务-routines/schedule.json", "03-定时任务-routines/schedule.zh-CN.json", "03-定时任务-routines/CONTINUITY.md",
           "03-定时任务-routines/CONTINUITY.zh-CN.md", "04-运行状态-state/readiness.json", "05-交易记录-data/current-state.json")


def due_slot(schedule, now):
    local = now.astimezone(ZoneInfo(schedule["timezone"]))
    if local.date().isoformat() not in schedule["planned_trading_dates"]:
        return None
    candidates = []
    for task in schedule["tasks"]:
        hour, minute = map(int, task["time"].split(":"))
        planned = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delay = local - planned
        if timedelta(0) <= delay <= timedelta(minutes=schedule["late_start_grace_minutes"]):
            candidates.append((delay, task["id"]))
    if candidates:
        _, task_id = min(candidates, key=lambda candidate: candidate[0])
        return local.date().isoformat() + "_" + task_id
    return None


def atomic_write(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def export_records(store):
    # Export deterministic per-run files; replay after a crash cannot duplicate entries.
    records = store.completed()
    for run_id, payload in records:
        atomic_write(ROOT / "05-交易记录-data" / "运行日志-journal" / (run_id + ".md"), payload["journal"])
        atomic_write(ROOT / "05-交易记录-data" / "证据资料-evidence" / (run_id + ".json"), json.dumps(payload["check"], indent=2) + "\n")
    # Portfolio JSON remains authoritative; run recovery never rolls it backwards.
    if records:
        run_id, payload = records[-1]
        if len(run_id) >= 10 and run_id[4:5] == "-" and run_id[7:8] == "-":
            report_date = run_id[:10]
        else:
            checked_at = payload.get("check", {}).get("checked_at")
            report_date = datetime.fromisoformat(checked_at.replace("Z", "+00:00")).astimezone(
                ZoneInfo("America/Chicago")
            ).date().isoformat()
        path = ROOT / "05-交易记录-data" / "current-state.json"
        state = json.loads(path.read_text())
        latest = state.get("last_run") or {}
        timestamp = payload["check"]["checked_at"]
        if latest.get("timestamp", "") <= timestamp:
            state["last_run"] = {"run_id": run_id, "timestamp": timestamp, "mode": "observation_only",
                                 "stock_api_verified": payload["check"].get("stock_etf_access_verified", False), "orders_placed": False}
            dates = state.get("planned_trading_dates", [])
            if report_date in dates:
                state["trading_day_index"] = dates.index(report_date) + 1
                if state.get("risk_date") != report_date:
                    state["risk_date"] = report_date
                    state["daily_realized_pnl_usdt"] = 0
                    if not state.get("positions"):
                        state["daily_open_risk_usdt"] = 0
            atomic_write(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        # Only refresh the latest trading day. Older Chinese reports are immutable snapshots.
        write_daily_report(report_date, ROOT)


def make_payload(run_id, check, state):
    journal = "\n".join([
        "# 只读观察记录", "", "- 运行编号：" + run_id,
        "- 记录时间：" + utc_now(),
        "- 本次操作：读取 Binance 股票接口，并保存实际验证结果。",
        "- 操作原因：在模拟交易判断前核对数据和账户读取状态。",
        "- 是否提出订单：否", "- 是否真实下单：否", "- 是否成交：否",
        "- 本地模拟持仓：" + json.dumps(state.get("positions", []), ensure_ascii=False),
        "- 本地模拟现金：" + str(state.get("cash_usdt")) + " USDT",
        "- 本地模拟未平仓风险：" + str(state.get("daily_open_risk_usdt")) + " USDT",
        "- 真实账户资产：本检查器不做真实资产对账。",
        "- 检查问题：" + json.dumps(check.get("errors", []), ensure_ascii=False),
        "- 下次重点：继续核对认证、股票行情读取和模拟交易风险。",
        "- 人工事项：认证失败时检查本地 API 设置；真实交易始终需要人工明确确认。",
        "- 证据文件：../evidence/" + run_id + ".json", "",
    ])
    return {"journal": journal, "check": check}


def supplemental_market_check():
    try:
        result = check_market_data()
    except (OSError, ValueError):
        result = {
            "checked_at": utc_now(),
            "provider": "yahoo_finance_public_chart",
            "credentials_required": False,
            "market_data_ready": False,
            "errors": ["Public market-data source is unavailable or invalid"],
        }
    update_market_data_readiness(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--manual", action="store_true")
    group.add_argument("--recover", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    schedule = json.loads((ROOT / "03-定时任务-routines/schedule.json").read_text())
    slot = due_slot(schedule, datetime.now(ZoneInfo("UTC")))
    if args.dry_run:
        print(json.dumps({"due_slot": slot, "planned_slots": len(schedule["planned_trading_dates"]) * len(schedule["tasks"])}))
        return 0
    if not args.manual and not args.recover and slot is None:
        print(json.dumps({"status": "outside_scheduled_window"}))
        return 0
    with (ROOT / "04-运行状态-state" / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "another_run_active"}))
            return 0
        store = RunStore(ROOT / "05-交易记录-data" / "runs.sqlite3")
        try:
            export_records(store)
            if args.recover:
                count = store.recover_read_only()
                print(json.dumps({"interrupted_runs_recorded": count, "exports_restored": True}))
                return 0
            for name in STARTUP:
                (ROOT / name).read_text(encoding="utf-8")
            journals = sorted((ROOT / "05-交易记录-data" / "运行日志-journal").glob("*.md"), key=lambda p: p.stat().st_mtime)
            if journals:
                journals[-1].read_text(encoding="utf-8")
            run_id = "manual_" + datetime.now().strftime("%Y%m%dT%H%M%S%f") if args.manual else slot
            if not store.begin(run_id):
                print(json.dumps({"status": "duplicate_skipped", "run_id": run_id}))
                return 0
            state = json.loads((ROOT / "05-交易记录-data" / "current-state.json").read_text())
            result = check_stocks(load_config(CONFIG))
            update_readiness(result)
            market_data = supplemental_market_check()
            result["supplemental_market_data"] = market_data
            if market_data.get("market_data_ready") is not True:
                result["errors"].append("supplemental_market_data: not ready for a new paper position")
            store.finish(run_id, make_payload(run_id, result, state))
            export_records(store)
            print(json.dumps({"run_id": run_id, "stock_api_verified": result["stock_etf_access_verified"], "errors": result["errors"]}, indent=2))
            return 0 if result["stock_etf_access_verified"] else 2
        finally:
            store.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({"error": "Observation incomplete; inspect local state and use --recover before next run"}))
        raise SystemExit(4)
