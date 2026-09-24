import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06-程序脚本-scripts"))

from paper_ledger import PaperLedger, PaperLedgerError


class PaperLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "05-交易记录-data").mkdir()
        (self.root / "04-运行状态-state").mkdir()
        self.now = datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc)
        self.state = {
            "planned_trading_dates": ["2026-09-15"],
            "starting_capital_usdt": 10000,
            "cash_usdt": 10000,
            "equity_usdt": 10000,
            "realized_pnl_usdt": 0,
            "unrealized_pnl_usdt": 0,
            "daily_realized_pnl_usdt": 0,
            "daily_open_risk_usdt": 0,
            "positions": [],
            "open_orders": [],
            "watchlist": ["AAPL", "SPY"],
        }
        self.readiness = {
            "paper_trading_only": True,
            "live_trading_enabled": False,
            "broker_connected": True,
            "human_confirmation_required_for_live_orders": True,
            "binance_stock_trading_eligibility_verified": True,
            "binance_stock_api_read_access_verified": True,
            "local_paper_ledger_initialized": True,
            "autonomous_paper_execution_enabled": True,
            "orders_allowed": False,
            "max_position_size_percent": 10,
            "max_daily_loss_percent": 2,
            "max_single_trade_loss_percent": 0.5,
            "binance_stocks_api": {
                "checked_at": self.now.isoformat(),
                "stock_etf_access_verified": True,
            },
        }
        self.config = {
            "fee_bps_per_side": "10",
            "slippage_bps_per_side": "2",
            "max_spread_bps": "25",
            "quote_max_age_seconds": "10",
            "readiness_max_age_hours": "24",
            "minimum_evidence_categories": 2,
            "minimum_reward_risk": "1.5",
            "regular_session_open_ct": "08:30",
            "new_entry_cutoff_ct": "11:30",
        }
        self.ledger_data = {"version": 1, "next_sequence": 1, "events": []}
        self._write_all()

    def _write_all(self):
        for path, payload in (
            (self.root / "05-交易记录-data/current-state.json", self.state),
            (self.root / "04-运行状态-state/readiness.json", self.readiness),
            (self.root / "04-运行状态-state/paper-config.json", self.config),
            (self.root / "05-交易记录-data/paper-ledger.json", self.ledger_data),
        ):
            path.write_text(json.dumps(payload), encoding="utf-8")

    def make_ledger(self):
        return PaperLedger(
            self.root / "05-交易记录-data/current-state.json",
            self.root / "04-运行状态-state/readiness.json",
            self.root / "04-运行状态-state/paper-config.json",
            self.root / "05-交易记录-data/paper-ledger.json",
        )

    def quote(self, bid="99.98", ask="100.00", bid_size="100", ask_size="100", received_at=None):
        return {
            "symbol": "AAPL",
            "bid": bid,
            "ask": ask,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "received_at": (received_at or self.now).isoformat(),
        }

    def rules(self):
        return {
            "symbol": "AAPL",
            "tradability": "BUY_SELL",
            "fractionable": True,
            "stepSize": "0.0001",
            "minQty": "0.0001",
            "maxQty": "1000",
            "minNotional": "5",
            "maxNotional": "1000000",
        }

    def request(self):
        return {
            "symbol": "AAPL",
            "quote": self.quote(),
            "rules": self.rules(),
            "stop_price": "95",
            "target_price": "109",
            "thesis": "Liquid large-cap trend continuation with defined invalidation.",
            "evidence": [
                {"category": "price_action", "source": "market snapshot"},
                {"category": "market_context", "source": "index context"},
            ],
        }

    def test_open_respects_position_and_trade_limits(self):
        ledger = self.make_ledger()
        event = ledger.open_long(self.request(), self.now)
        state = json.loads((self.root / "05-交易记录-data/current-state.json").read_text())
        position = state["positions"][0]
        self.assertEqual(event["action"], "open_long")
        self.assertLessEqual(Decimal(position["entry_price"]) * Decimal(position["quantity"]), Decimal("1000"))
        self.assertLessEqual(Decimal(position["planned_loss_usdt"]), Decimal("50"))
        self.assertLess(state["cash_usdt"], 10000)
        self.assertFalse(event.get("live_order_sent", False))

    def test_new_session_resets_daily_loss_and_updates_progress(self):
        self.state["risk_date"] = "2026-09-14"
        self.state["daily_realized_pnl_usdt"] = -100
        self._write_all()
        ledger = self.make_ledger()
        ledger._roll_trading_day(self.now)
        self.assertEqual(ledger.state["risk_date"], "2026-09-15")
        self.assertEqual(ledger.state["daily_realized_pnl_usdt"], 0)
        self.assertEqual(ledger.state["trading_day_index"], 1)

    def test_rejects_single_evidence_category(self):
        request = self.request()
        request["evidence"] = [{"category": "price_action", "source": "one source"}]
        with self.assertRaisesRegex(PaperLedgerError, "two independent"):
            self.make_ledger().open_long(request, self.now)

    def test_rejects_stale_quote(self):
        request = self.request()
        request["quote"] = self.quote(received_at=self.now - timedelta(seconds=11))
        with self.assertRaisesRegex(PaperLedgerError, "stale"):
            self.make_ledger().open_long(request, self.now)

    def test_rejects_wide_spread(self):
        request = self.request()
        request["quote"] = self.quote(bid="99", ask="100")
        with self.assertRaisesRegex(PaperLedgerError, "Spread"):
            self.make_ledger().open_long(request, self.now)

    def test_live_enabled_blocks_paper_action(self):
        self.readiness["live_trading_enabled"] = True
        self._write_all()
        with self.assertRaisesRegex(PaperLedgerError, "live_trading_enabled"):
            self.make_ledger().open_long(self.request(), self.now)

    def test_after_cutoff_blocks_new_entry(self):
        late = datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)
        self.readiness["binance_stocks_api"]["checked_at"] = late.isoformat()
        self._write_all()
        request = self.request()
        request["quote"]["received_at"] = late.isoformat()
        with self.assertRaisesRegex(PaperLedgerError, "outside"):
            self.make_ledger().open_long(request, late)

    def test_stop_exit_updates_realized_pnl(self):
        ledger = self.make_ledger()
        ledger.open_long(self.request(), self.now)
        stop_time = self.now + timedelta(minutes=5)
        ledger.readiness["binance_stocks_api"]["checked_at"] = stop_time.isoformat()
        stop_quote = self.quote(bid="94.90", ask="95.00", received_at=stop_time)
        event = ledger.mark({"quote": stop_quote}, stop_time, evaluate=True)
        state = json.loads((self.root / "05-交易记录-data/current-state.json").read_text())
        self.assertEqual(event["action"], "close")
        self.assertEqual(event["reason"], "stop")
        self.assertEqual(state["positions"], [])
        self.assertLess(state["realized_pnl_usdt"], 0)
        self.assertEqual(state["daily_open_risk_usdt"], 0)

    def test_quote_size_caps_entry_and_blocks_unsupported_exit(self):
        request = self.request()
        request["quote"] = self.quote(ask_size="1")
        ledger = self.make_ledger()
        ledger.open_long(request, self.now)
        position = ledger.state["positions"][0]
        self.assertLessEqual(Decimal(position["quantity"]), Decimal("1"))
        exit_time = self.now + timedelta(minutes=1)
        ledger.readiness["binance_stocks_api"]["checked_at"] = exit_time.isoformat()
        with self.assertRaisesRegex(PaperLedgerError, "bid size"):
            ledger.close({
                "quote": self.quote(bid_size="0.5", received_at=exit_time),
                "reason": "manual_exit",
            }, exit_time)

    def test_reconcile_restores_last_event_snapshot(self):
        self.make_ledger().open_long(self.request(), self.now)
        damaged = json.loads((self.root / "05-交易记录-data/current-state.json").read_text())
        damaged["cash_usdt"] = 1
        (self.root / "05-交易记录-data/current-state.json").write_text(json.dumps(damaged), encoding="utf-8")
        restored = self.make_ledger().reconcile()
        self.assertGreater(restored["cash_usdt"], 1)
        self.assertEqual(len(restored["positions"]), 1)


if __name__ == "__main__":
    unittest.main()
