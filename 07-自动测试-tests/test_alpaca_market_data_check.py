import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06-程序脚本-scripts"))

import alpaca_market_data_check as market_data


class AlpacaMarketDataTests(unittest.TestCase):
    def test_config_rejects_non_official_host(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "market.env"
            path.write_text(
                "ALPACA_API_KEY_ID=test\n"
                "ALPACA_API_SECRET_KEY=test\n"
                "ALPACA_DATA_BASE_URL=https://example.com\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                market_data.load_config(path)

    def test_fresh_snapshots_verify_volume_and_vwap(self):
        now = datetime(2026, 9, 24, 14, 0, tzinfo=timezone.utc)
        config = {
            "ALPACA_API_KEY_ID": "test",
            "ALPACA_API_SECRET_KEY": "test",
            "ALPACA_DATA_BASE_URL": market_data.ALLOWED_BASE,
            "ALPACA_DATA_FEED": "iex",
            "ALPACA_SYMBOLS": "SPY,QQQ",
            "ALPACA_MAX_AGE_SECONDS": "300",
        }
        snapshots = {
            symbol: {
                "latestQuote": {"bp": 100, "ap": 100.01},
                "minuteBar": {"v": 1000, "vw": 100.005, "t": "2026-09-24T13:59:00Z"},
            }
            for symbol in ("SPY", "QQQ")
        }
        session = {"bars": {
            symbol: [
                {"v": 1000, "vw": 100, "t": "2026-09-24T13:58:00Z"},
                {"v": 1200, "vw": 101, "t": "2026-09-24T13:59:00Z"},
            ]
            for symbol in ("SPY", "QQQ")
        }}
        daily = {"bars": {
            symbol: [
                {"v": 1000000 + index, "t": "2026-09-%02dT04:00:00Z" % (index + 1)}
                for index in range(20)
            ]
            for symbol in ("SPY", "QQQ")
        }}
        with patch.object(
            market_data,
            "get_json",
            side_effect=((snapshots, None), (session, None), (daily, None)),
        ):
            result = market_data.check(config, now=now)
        self.assertTrue(result["market_data_ready"])
        self.assertTrue(result["minute_volume_vwap_verified"])
        self.assertTrue(result["session_bars_verified"])
        self.assertTrue(result["recent_daily_volume_verified"])


if __name__ == "__main__":
    unittest.main()
