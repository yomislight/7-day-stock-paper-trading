# Automation Description and Saved Prompt

This is the checked-in companion to the active GPT heartbeat. See [automation-status.json](automation-status.json) for the current deployment status.

## Active Schedule

Use `/Users/a123/Desktop/7天股票交易实验` and return to the existing experiment conversation. Six America/Chicago checks: 07:45, 08:35, 11:00, 13:00, 14:15 and 14:45. Round-two dates are in [schedule.json](schedule.json) and its [Chinese companion](schedule.zh-CN.json): 42 occurrences and a 30-minute late-start tolerance. Each slot has an independent GPT heartbeat, while local launchd polls every five minutes as a read-only fallback. The GitHub-hosted runner remains blocked by Binance HTTP 451.

## Saved Prompt

Perform all project operations only in the Desktop experiment directory. Read both languages of AGENTS, strategy, schedule and CONTINUITY, plus readiness, current-state and the latest journal.

All user-facing reports must be in Chinese. At the end of every run, invoke the Chinese daily-report generator so cash, holdings, paper actions, profit/loss, no-trade reasons, risk and next steps are summarized in `09-每日中文报告-daily-reports/YYYY-MM-DD-每日交易报告.md`. Add a concise Chinese `reason_zh` to every structured decision and `data_gap_zh` when data is incomplete. The end-of-day task must save a verifiable Chinese market recap to `05-交易记录-data/证据资料-evidence/YYYY-MM-DD-market-summary.zh-CN.json`, including major-index changes and closes, rates, oil, the main market narrative, sector structure, implications for decisions, next-session risks and source links. The report must separately explain why the system bought or did not buy and why it sold or did not sell. It must distinguish a deliberate market decision from missed, late or incomplete execution, then include a daily review and concrete items for joint revision. Never present a missed run as a successful no-trade decision.

Run `python3 -B 06-程序脚本-scripts/run_observation.py --dry-run` first. Outside the planned sessions or 30-minute slot tolerance, report that there is no valid execution window and never backfill a trade. For a due slot, run `python3 -B 06-程序脚本-scripts/run_observation.py`. A `duplicate_skipped` result means the local fallback already saved read-only evidence, so continue with research, the paper decision and reporting. Reconcile an active or interrupted read-only run before continuing.

Research the slot's topic with official calendars, news and verifiable data. Save research in separate journal/evidence files using the same run_id with a `-research` suffix, and update next-task focus. Do not edit generated API journals.

After research, independently decide whether the local paper ledger should open, manage, close, or record no trade. The user authorized autonomous paper decisions only. Never submit a real Binance order, transfer, tokenization request, or account-setting change.

For every decision, create a non-secret JSON file under `05-交易记录-data/决策记录-decisions/` with `paper_trading_only: true`, an `action` of `open_long`, `manage`, `close`, or `no_trade`, and the evidence, thesis, stop, and target required for an entry. Then run `python3 -B 06-程序脚本-scripts/paper_engine.py --decision <file> --run-id <date_slot>_paper`; the `_paper` suffix prevents overwriting the read-only runner's evidence file. The engine refreshes read-only Stocks data, rejects stale or unsafe state, and writes only to the local paper ledger. Do not create an entry before 08:30 Central or after 11:30 Central. At 14:15 Central, close any remaining paper position because overnight holds are disabled.

Keep 10000 USDT paper capital and existing limits; record no trade when actual fees, liquidity, data quality, or evidence make trading infeasible. This is not a continuous stop monitor. Read credentials locally through the script; never display them.

Stay quiet for unchanged or non-actionable state. Notify on scheduled reports, meaningful changes, completion, failure or required user action. Revalidate seven sessions and synchronize schedules if the start is delayed. Pause after the seventh session.

## Verification Boundary

All 42 round-two times and bilingual schedules were checked offline. Round one completed only six scheduled slots and does not count as a finished seven-day experiment. Round two is complete only when `experiment_status.py` confirms all six read-only checks, six paper decisions, the Chinese report and end-of-day market recap for each of seven sessions.
