import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06-程序脚本-scripts"))

import public_market_data_check as market_data


def epoch(moment):
    return int(moment.timestamp())


class PublicMarketDataTests(unittest.TestCase):
    def test_symbols_are_restricted(self):
        with self.assertRaises(ValueError):
            market_data.normalize_symbols(["AAPL", "../../secret"])

    def test_fresh_chart_verifies_volume_and_derived_vwap(self):
        now = datetime(2026, 9, 24, 14, 5, tzinfo=timezone.utc)
        new_york = market_data.NEW_YORK
        timestamps = []
        opens, highs, lows, closes, volumes = [], [], [], [], []
        for offset in range(20, 0, -1):
            local = (now.astimezone(new_york) - timedelta(days=offset)).replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            timestamps.append(epoch(local.astimezone(timezone.utc)))
            opens.append(99.0)
            highs.append(101.0)
            lows.append(98.0)
            closes.append(100.0)
            volumes.append(1_000_000)
        for minute, close in ((30, 100.0), (35, 101.0), (40, 102.0), (45, 103.0), (50, 104.0), (55, 105.0), (0, 106.0)):
            hour = 10 if minute == 0 else 9
            local = now.astimezone(new_york).replace(hour=hour, minute=minute, second=0, microsecond=0)
            timestamps.append(epoch(local.astimezone(timezone.utc)))
            opens.append(close - 0.5)
            highs.append(close + 0.5)
            lows.append(close - 1.0)
            closes.append(close)
            volumes.append(10_000)
        payload = {
            "chart": {
                "error": None,
                "result": [{
                    "meta": {"chartPreviousClose": 99.0},
                    "timestamp": timestamps,
                    "indicators": {"quote": [{
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes,
                    }]},
                }],
            }
        }

        result = market_data.check(["AAPL"], now=now, fetcher=lambda symbol: (payload, None))

        self.assertTrue(result["market_data_ready"])
        self.assertEqual(result["verified_symbols"], ["AAPL"])
        self.assertTrue(result["session_volume_verified"])
        self.assertTrue(result["derived_vwap_verified"])
        self.assertEqual(result["symbols"]["AAPL"]["history_session_count"], 20)

    def test_missing_current_session_fails_closed(self):
        now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
        payload = {"chart": {"error": None, "result": [{
            "meta": {},
            "timestamp": [],
            "indicators": {"quote": [{"open": [], "high": [], "low": [], "close": [], "volume": []}]},
        }]}}
        result = market_data.check(["SPY"], now=now, fetcher=lambda symbol: (payload, None))
        self.assertFalse(result["market_data_ready"])
        self.assertEqual(result["verified_symbols"], [])


if __name__ == "__main__":
    unittest.main()
