#!/usr/bin/env python3
"""Audit whether the seven-day experiment has complete six-slot records."""

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def completed_run_ids(path):
    if not path.exists():
        return set()
    connection = sqlite3.connect(path)
    try:
        return {row[0] for row in connection.execute("SELECT run_id FROM runs WHERE status='complete'")}
    finally:
        connection.close()


def build_status(root=ROOT):
    root = Path(root)
    schedule = json.loads((root / "03-定时任务-routines" / "schedule.json").read_text(encoding="utf-8"))
    run_ids = completed_run_ids(root / "05-交易记录-data" / "runs.sqlite3")
    decisions = root / "05-交易记录-data" / "决策记录-decisions"
    reports = root / "09-每日中文报告-daily-reports"
    evidence = root / "05-交易记录-data" / "证据资料-evidence"
    rows = []
    for date in schedule["planned_trading_dates"]:
        expected = [date + "_" + task["id"] for task in schedule["tasks"]]
        observed = [run_id for run_id in expected if run_id in run_ids]
        decided = [run_id for run_id in expected if (decisions / (run_id + ".json")).exists()]
        report_ready = (reports / (date + "-每日交易报告.md")).exists()
        market_summary_ready = (evidence / (date + "-market-summary.zh-CN.json")).exists()
        complete = (
            len(observed) == len(expected)
            and len(decided) == len(expected)
            and report_ready
            and market_summary_ready
        )
        rows.append({
            "date": date,
            "read_only_checks": len(observed),
            "paper_decisions": len(decided),
            "daily_report": report_ready,
            "market_summary": market_summary_ready,
            "complete": complete,
            "missing_read_only": [item for item in expected if item not in observed],
            "missing_decisions": [item for item in expected if item not in decided],
        })
    return {
        "experiment_round": schedule.get("experiment_round"),
        "planned_trading_days": len(rows),
        "planned_slots": len(rows) * len(schedule["tasks"]),
        "read_only_slots_completed": sum(item["read_only_checks"] for item in rows),
        "paper_decisions_completed": sum(item["paper_decisions"] for item in rows),
        "fully_completed_trading_days": sum(item["complete"] for item in rows),
        "experiment_complete": bool(rows) and all(item["complete"] for item in rows),
        "days": rows,
    }


def main():
    print(json.dumps(build_status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
