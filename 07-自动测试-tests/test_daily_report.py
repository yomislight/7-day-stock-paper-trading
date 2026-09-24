import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06-程序脚本-scripts"))

from daily_report import due_scheduled_slots, write_daily_report


class DailyReportTests(unittest.TestCase):
    def test_current_day_does_not_mark_future_slots_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routines = root / "03-定时任务-routines"
            routines.mkdir(parents=True)
            routines.joinpath("schedule.json").write_text(json.dumps({
                "tasks": [
                    {"id": "pre_market_0745_ct", "time": "07:45"},
                    {"id": "open_review_0835_ct", "time": "08:35"},
                    {"id": "late_morning_1100_ct", "time": "11:00"},
                    {"id": "midday_1300_ct", "time": "13:00"},
                    {"id": "flatten_prep_1415_ct", "time": "14:15"},
                    {"id": "end_of_day_1445_ct", "time": "14:45"},
                ]
            }), encoding="utf-8")
            now = datetime(2026, 9, 24, 9, 0, tzinfo=ZoneInfo("America/Chicago"))
            self.assertEqual(
                due_scheduled_slots(root, "2026-09-24", now),
                ("pre_market_0745_ct", "open_review_0835_ct"),
            )

    def test_writes_human_readable_chinese_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "05-交易记录-data"
            (data / "决策记录-decisions").mkdir(parents=True)
            (data / "运行日志-journal").mkdir()
            (data / "current-state.json").write_text(json.dumps({
                "planned_trading_dates": ["2026-09-15"],
                "starting_capital_usdt": 10000,
                "cash_usdt": 10000,
                "equity_usdt": 10000,
                "positions": [],
                "daily_open_risk_usdt": 0,
                "next_task_focus": "下次继续观察。",
            }), encoding="utf-8")
            (data / "paper-ledger.json").write_text('{"events": []}', encoding="utf-8")
            (data / "决策记录-decisions" / "2026-09-15_pre_market_0745_ct.json").write_text(json.dumps({
                "action": "no_trade",
                "reason_zh": "盘前证据不足，保持现金。",
            }, ensure_ascii=False), encoding="utf-8")

            path = write_daily_report("2026-09-15", root)
            text = path.read_text(encoding="utf-8")

            self.assertEqual(path.parent.name, "09-每日中文报告-daily-reports")
            self.assertIn("每日交易中文报告", text)
            self.assertIn("当日美股大行情", text)
            self.assertIn("当天没有模拟成交", text)
            self.assertIn("盘前证据不足，保持现金", text)
            self.assertIn("为什么没有买入", text)
            self.assertIn("为什么没有卖出", text)
            self.assertIn("当日复盘", text)
            self.assertIn("我们需要一起修改什么", text)
            self.assertIn("真实资金交易：没有", text)


if __name__ == "__main__":
    unittest.main()
