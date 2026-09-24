# Binance API Setup

This project keeps Binance credentials local and uses the API in read-only mode unless a specific live order is explicitly confirmed in chat.

## Files

- `10-API密钥-仅本地-local-secrets/binance-api.env`: dedicated local Binance API credential file. This file is ignored by git.
- `10-API密钥-仅本地-local-secrets/binance-api.env.example`: safe Binance API template without secrets.
- `.env`: general local safety switches. This file is ignored by git.
- `.env.example`: safe general template without secrets.
- `06-程序脚本-scripts/binance_readiness_check.py`: read-only verification script.
- `04-运行状态-state/readiness.json`: project readiness state used by trading runs.

## Configure Credentials

1. Open `10-API密钥-仅本地-local-secrets/binance-api.env` locally.
2. Fill `BINANCE_API_KEY` and `BINANCE_API_SECRET`.
3. Keep these values unchanged unless there is a specific reason:

```env
BINANCE_ENV=production
BINANCE_BASE_URL=https://api.binance.com
BINANCE_ALLOW_TRADING=false
BINANCE_REQUIRE_READ_ONLY=true
PAPER_TRADING_ONLY=true
LIVE_TRADING_ENABLED=false
HUMAN_CONFIRMATION_REQUIRED_FOR_LIVE_ORDERS=true
```

For Binance Demo Mode Spot API, use:

```env
BINANCE_ENV=demo
BINANCE_BASE_URL=https://demo-api.binance.com
```

For Binance Spot Testnet, use:

```env
BINANCE_ENV=testnet
BINANCE_BASE_URL=https://testnet.binance.vision
```

## Verify

Run:

```bash
python3 06-程序脚本-scripts/binance_readiness_check.py
```

To update `04-运行状态-state/readiness.json` with the safe verification result:

```bash
python3 06-程序脚本-scripts/binance_readiness_check.py --update-readiness
```

To use a different local Binance config file:

```bash
python3 06-程序脚本-scripts/binance_readiness_check.py --config /path/to/binance-api.env --update-readiness
```

The script prints only readiness metadata. It does not print API secrets, raw account JSON, balances, or order data.

## Important Boundary

Binance Spot/Demo/Testnet APIs can verify Binance API connectivity and signed account access. They do not by themselves verify U.S. stock/ETF trading eligibility. The project must keep `binance_stock_trading_eligibility_verified`, `binance_stock_api_read_access_verified`, `binance_paper_trading_available_verified`, and `orders_allowed` false until a documented stock/ETF API path is verified.
