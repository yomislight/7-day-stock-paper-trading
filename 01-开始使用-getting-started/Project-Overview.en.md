# Seven-Day Stock Trading Experiment

Project directory: `/Users/a123/Desktop/7天股票交易实验`.

This is a Binance Stocks research and local paper-trading experiment. Read-only authentication, execution journaling and the local paper ledger are implemented. Live trading remains disabled.

## Navigation

| Topic | File |
| --- | --- |
| Decisions, status and next steps | [Project handoff](../02-项目文档-docs/PROJECT-HANDOFF.md) |
| Local setup and commands | [Getting started, Chinese](开始使用.md) |
| Binance endpoints | [API integration](../02-项目文档-docs/BINANCE-API.md) |
| Stop/fill proposal | [Draft v0.1](../02-项目文档-docs/STOP-AND-FILL-DRAFT.md) |
| Existing strategy | [Trading strategy](../02-项目文档-docs/TRADING-STRATEGY.md) |
| Agent operating rules | [AGENTS](../AGENTS.md) |
| Recovery and scheduling | [Continuity](../03-定时任务-routines/CONTINUITY.md), [Automation prompt](../03-定时任务-routines/AUTOMATION-PROMPT.md) |
| Validation | [Validation record](../05-交易记录-data/证据资料-evidence/2026-09-14-validation.md) |
| Chinese overview | [README Chinese](../README.md) |

## Saved Status as of 2026-09-16

Credentials are locally configured and ignored by Git. Signed account and Binance Stocks read checks have passed. Twenty-seven automated tests pass. SQLite records, concurrency protection, export recovery and a local paper fill ledger are implemented. GPT heartbeat automation 7 is active for 42 scheduled occurrences. GitHub-hosted runners remain blocked by Binance HTTP 451. There is no live-order implementation or continuous risk monitor. Paper cash is 10000 USDT, with no positions at the latest saved state.

Current authority: [readiness](../04-运行状态-state/readiness.json), [portfolio state](../05-交易记录-data/current-state.json), [automation status](../03-定时任务-routines/automation-status.json) and the latest evidence.

## Layout and Ownership

The repository uses numbered Chinese categories. `02-项目文档-docs/` contains strategy and integration documents; `03-定时任务-routines/` contains schedules and continuity; `06-程序脚本-scripts/` and `07-自动测试-tests/` contain implementation and tests. `04-运行状态-state/` tracks readiness; `05-交易记录-data/` holds the paper portfolio, SQLite execution records, journals and evidence.

The original Alpaca PDF remains reference material, not the Binance implementation's instructions. Earlier work in the Documents project was not merged into the Desktop experiment. All subsequent project changes belong here. Both Chinese and English documents remain available.

Real credentials stay only in `10-API密钥-仅本地-local-secrets/binance-api.env`. Share `10-API密钥-仅本地-local-secrets/binance-api.env.example`, not the completed file, editor swap files or backups. Git ignore rules do not filter Finder copies or archives.
