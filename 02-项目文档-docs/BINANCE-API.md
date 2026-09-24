# Binance Stocks API Integration

Production base URL: https://api.binance.com. Local HMAC credentials: root 10-API密钥-仅本地-local-secrets/binance-api.env. No credentials are read from other projects. Default checker scope is Stocks; --spot-only is a diagnostic option.

| Purpose | GET path | Authentication |
| --- | --- | --- |
| Clock | /api/v3/time | Public |
| Spot account diagnostic | /api/v3/account | Signed |
| API permissions | /sapi/v1/account/apiRestrictions | Signed |
| Stock rules | /sapi/v1/equity/market/exchangeInfo?symbol=AAPL | API key |
| Stock quote | /sapi/v1/equity/market/quote?symbol=AAPL | API key |
| Open stock orders | /sapi/v1/equity/order/open-orders | Signed |

Only GET requests are implemented. Separate verification fields record each endpoint. A valid quote does not prove market freshness, region eligibility or permission to trade. Spot testnet does not establish a Stocks sandbox. No verified Stocks paper endpoint is configured.

The original Alpaca PDF remains a reference. This document and its Chinese companion are the project-specific Binance adaptation, not a claim that the PDF's Alpaca endpoints work at Binance. Ordinary stocks use tickers such as AAPL, not SPYUSDT. Potential future ordinary-stock execution must explicitly set tokenize=false; no execution code is included.

API error -2015 means the key, IP or permissions were rejected. Check that the local pair belongs to Binance.com production, uses HMAC, has reading enabled, and matches the API IP allowlist. Do not bypass regional restrictions or accept account agreements automatically. No raw API errors, balances, keys or signatures are exported.

Run `python3 -B 06-程序脚本-scripts/binance_readiness_check.py --update-readiness` from the project. Exit 0 means the requested scope passed, 2 means credentials/account/Stocks access did not pass, 3 means public connectivity failed, and 4 means local files need checking. An empty quote or empty symbol list is not a successful Stocks verification.

Sources: [Market data](https://developers.binance.com/en/docs/catalog/advanced-trading-stocks-trading/api/rest-api/market-data), [Stock orders](https://developers.binance.com/en/docs/catalog/advanced-trading-stocks-trading/api/rest-api/trade), [API permissions](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account).
