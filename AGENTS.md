# AI Trading Experiment Operating Rules

This project is a 7 trading day stock/ETF research and paper trading experiment.
It is not a live trading system and must not be described as a profitable system.

## Safety Defaults

- Default mode is paper trading only.
- Live trading is disabled unless the user explicitly authorizes a specific live order in chat.
- Never place a real-money order without human confirmation.
- If any readiness check is missing, false, stale, or ambiguous, do not place orders.
- If market conditions are unclear, choose observation over trading.
- Risk control has priority over returns.

## Platform Scope

- Target platform: Binance stock/ETF trading capability.
- Before any execution path is used, verify whether Binance account permissions, region eligibility, API support, and any paper/sandbox capability are available.
- If Binance does not expose paper trading for stocks/ETFs, use the local paper ledger in this project.
- Binance API keys must stay local in the root `10-API密钥-仅本地-local-secrets/binance-api.env`; never ask the user to paste keys in chat. The read-only checker reads only this file. Share `10-API密钥-仅本地-local-secrets/binance-api.env.example`, never the completed credential file.
- Binance is the source for stock rules and final executable quotes. A keyless public chart source supplies five-minute bars, volume context, and a derived VWAP for paper research only. Missing, stale, or incomplete supplemental data blocks new paper positions but must never block risk reduction. Never describe the public bars as official consolidated SIP data.

## Permitted Work

- Read strategy, schedules, state, journal, and evidence.
- Perform read-only account, position, order, and market-data checks when credentials are locally available.
- Produce watchlists, risk notes, and paper trade records.
- In paper trading only, autonomously decide whether to buy, sell, reduce, stop out, flatten, hold, or stay in cash according to the strategy and risk limits.
- Autonomous paper execution requires `autonomous_paper_execution_enabled: true` in readiness and writes only to the local ledger through `06-程序脚本-scripts/paper_engine.py`.
- Record no-trade decisions with evidence and reasons.

## Prohibited Work

- No live orders without explicit user confirmation.
- No options, futures, margin, leveraged products, crypto perpetuals, low-liquidity stocks, penny stocks, or unclear tokenized securities.
- No orders based on a single news item or a single indicator.
- No full-account or heavy-position trades.
- No credential leakage into journal, evidence files, logs, or chat.
- Paper trading autonomy does not authorize live trading, live order submission, transfers, account setting changes, or enabling trading permissions.

## Required Startup Reads

Every scheduled run must read these files before taking action:

- `AGENTS.md`
- `AGENTS.zh-CN.md`
- `02-项目文档-docs/TRADING-STRATEGY.md`
- `02-项目文档-docs/TRADING-STRATEGY.zh-CN.md`
- `03-定时任务-routines/schedule.json`
- `03-定时任务-routines/schedule.zh-CN.json`
- `03-定时任务-routines/CONTINUITY.md`
- `03-定时任务-routines/CONTINUITY.zh-CN.md`
- `04-运行状态-state/readiness.json`
- `05-交易记录-data/current-state.json`
- Latest file in `05-交易记录-data/运行日志-journal/`, if present

## Required End-of-Run Writes

Every scheduled run must update:

- `05-交易记录-data/current-state.json`
- The current trading day's journal file in `05-交易记录-data/运行日志-journal/`
- Evidence notes in `05-交易记录-data/证据资料-evidence/`
- The current day's fully Chinese summary in `09-每日中文报告-daily-reports/`

Each journal entry must state:

- What was done
- Why it was done
- Whether an order was proposed
- Whether an order was placed
- Whether an order filled
- Current holdings
- Current cash
- Current risk
- Next task focus
- Human confirmations needed

## Binance Runtime

- Use `02-项目文档-docs/BINANCE-API.md` and its Chinese companion for the Stocks endpoint mapping. The default checker uses `/sapi/v1/equity/`, not Spot symbol probes.
- `06-程序脚本-scripts/run_observation.py` is read-only. `06-程序脚本-scripts/paper_engine.py` may simulate local paper fills only; it has no broker POST path.
- The approved local paper rules enforce one position, 10% maximum notional, 0.5% maximum planned loss, two evidence categories, 1.5 net reward/risk, no new entry after 11:30 Central, and no overnight position.
- Preserve both languages. Round-two dates are authoritative in the bilingual schedule; do not count setup, manual checks, missed slots, or backfilled reports as completed experiment sessions.
