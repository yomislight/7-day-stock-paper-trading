import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06-程序脚本-scripts"))
from run_store import RunStore
import run_observation as runner


class RuntimeTests(unittest.TestCase):
    def test_duplicate_and_interrupted_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            store = RunStore(Path(temp) / "runs.db")
            self.addCleanup(store.close)
            self.assertTrue(store.begin("day_slot"))
            with self.assertRaises(RuntimeError):
                store.begin("next_slot")
            store.finish("day_slot", {"check": {"orders_allowed": False}})
            self.assertFalse(store.begin("day_slot"))
            self.assertTrue(store.begin("next_slot"))
            self.assertEqual(store.recover_read_only(), 1)
            self.assertFalse(store.begin("next_slot"))
            self.assertTrue(store.begin("third_slot"))

    def test_two_connections_cannot_start_two_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.db"
            first, second = RunStore(path), RunStore(path)
            self.addCleanup(first.close)
            self.addCleanup(second.close)
            first.begin("first")
            with self.assertRaises(RuntimeError):
                second.begin("second")

    def test_all_42_slots_and_japan_conversion(self):
        schedule = json.loads((ROOT / "03-定时任务-routines" / "schedule.json").read_text())
        ids = set()
        for day in schedule["planned_trading_dates"]:
            for task in schedule["tasks"]:
                now = datetime.fromisoformat(day + "T" + task["time"]).replace(tzinfo=ZoneInfo("America/Chicago"))
                slot = runner.due_slot(schedule, now.astimezone(ZoneInfo("Asia/Tokyo")))
                self.assertIsNotNone(slot)
                ids.add(slot)
        self.assertEqual(len(ids), 42)
        for timestamp in ("2026-09-19T09:30", "2026-09-23T09:30", "2026-09-14T09:41"):
            self.assertIsNone(runner.due_slot(schedule, datetime.fromisoformat(timestamp).replace(tzinfo=ZoneInfo("America/Chicago"))))

    def test_bilingual_schedule_matches(self):
        en = json.loads((ROOT / "03-定时任务-routines/schedule.json").read_text())
        zh = json.loads((ROOT / "03-定时任务-routines/schedule.zh-CN.json").read_text())
        for key in ("timezone", "planned_trading_dates", "late_start_grace_minutes", "activation_status"):
            self.assertEqual(en[key], zh[key])
        self.assertEqual([(t["id"], t["time"]) for t in en["tasks"]], [(t["id"], t["time"]) for t in zh["tasks"]])

    def test_export_recovery_preserves_portfolio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("05-交易记录-data/运行日志-journal", "05-交易记录-data/证据资料-evidence"):
                (root / name).mkdir(parents=True)
            state_path = root / "05-交易记录-data/current-state.json"
            state_path.write_text(json.dumps({"cash_usdt": 17, "positions": [{"symbol": "EXAMPLE"}]}))
            store = RunStore(root / "runs.db")
            self.addCleanup(store.close)
            store.begin("one")
            store.finish("one", {"journal": "one entry", "check": {"checked_at": "2026-09-14T00:00:00+00:00", "stock_etf_access_verified": False}})
            with patch.object(runner, "ROOT", root):
                runner.export_records(store)
                runner.export_records(store)
            state = json.loads(state_path.read_text())
            self.assertEqual(state["cash_usdt"], 17)
            self.assertEqual(state["positions"], [{"symbol": "EXAMPLE"}])
            self.assertEqual(state["last_run"]["run_id"], "one")
            self.assertEqual(len(list((root / "05-交易记录-data/运行日志-journal").glob("*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
