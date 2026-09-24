# Evidence - 2026-09-15 Binance Readiness Success

## Run Context

- Local timestamp: 2026-09-15T10:50:06+09:00
- U.S. Central timestamp: 2026-09-14T20:50:06-05:00
- UTC timestamp: 2026-09-15T01:50:06Z
- Working directory: `/Users/a123/Desktop/7天股票交易实验`
- Config file checked: `10-API密钥-仅本地-local-secrets/binance-api.env`
- Mode: read-only readiness check
- Orders/transfers/settings changes: none

## Result Summary

- Config valid: true
- Credentials present: true
- Public Binance API reachable: true
- Signed account read verified: true
- API key permissions verified: true
- Stock/ETF access verified: true
- Stock rules read verified: true
- Stock quote read verified: true
- Stock open-orders read verified: true
- Quote freshness verified: false because the quote endpoint does not provide an exchange timestamp.
- Orders allowed by project: false

## AAPL Probe

- Symbol: AAPL
- Tradability: BUY_SELL
- Fractionable: true
- Extended-hours fractionable: true
- Minimum notional: 5.00000000
- Maximum notional: 1000000.00000000
- Bid: 331.55
- Ask: 332.11
- Quote received at: 2026-09-15T01:49:59.512846+00:00

## Key Permission Snapshot

- Enable Reading: true
- Enable Spot & Margin Trading: false
- Enable Withdrawals: false
- IP restricted: false

## Safety Decision

Read access is verified. Live trading remains disabled. Orders remain disallowed by project readiness. Continue paper trading only unless the user explicitly authorizes a specific live order in the future.
