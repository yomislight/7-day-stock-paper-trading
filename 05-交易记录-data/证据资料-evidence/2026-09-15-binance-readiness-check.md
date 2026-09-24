# Evidence - 2026-09-15 Binance Readiness Check

## Run Context

- Local timestamp: 2026-09-15T10:40:24+09:00
- U.S. Central timestamp: 2026-09-14T20:40:24-05:00
- UTC timestamp: 2026-09-15T01:40:24Z
- Working directory: `/Users/a123/Desktop/7天股票交易实验`
- Config file checked: `10-API密钥-仅本地-local-secrets/binance-api.env`
- Mode: read-only readiness check
- Orders/transfers/settings changes: none

## Result Summary

- Credentials present: true
- Public Binance API reachable: true
- Signed account read verified: false
- API key permissions verified: false
- Stock/ETF access verified: false
- Stock rules read verified: false
- Stock quote read verified: false
- Stock orders read verified: false
- Orders allowed by project: false

## Binance Error Codes Observed

- Account read: HTTP 401 / Binance -2015
- Stock rules: HTTP 400 / Binance -2015
- Stock quote: HTTP 400 / Binance -2015
- Stock orders: HTTP 400 / Binance -2015
- API permissions: HTTP 400 / Binance -2015

## Interpretation

The key/secret values are present and the public Binance API is reachable, but signed endpoints reject the credentials. This usually means one or more of the following:

- API key or secret was copied incorrectly.
- API key is restricted to a different IP address than this machine/network.
- API key was created for a different environment or account.
- Required read permissions are not enabled.
- Binance stock/equity endpoints are not enabled for this account or region.
- Key is not active yet or has been revoked.

## Safety Decision

Observation only. Do not place paper or live orders through Binance. Continue using local paper ledger only until signed read access and stock/ETF access are verified.
