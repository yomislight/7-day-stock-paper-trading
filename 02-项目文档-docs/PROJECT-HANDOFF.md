# Project Handoff

Updated 2026-09-14. This captures relevant decisions, implementation, evidence and pending work from the conversation. It is a snapshot; newer state files and evidence take precedence.

## Agreed Direction

All project changes belong in `/Users/a123/Desktop/7天股票交易实验`. Connect to actual Binance.com Stocks APIs using the dedicated local credential file. Real API connectivity is not live-order authorization. Alpaca is not in the runtime path because the user cannot complete its brokerage onboarding as a Japan resident. Keyless public five-minute bars may supplement paper research but are not official SIP data. Preserve both languages, keep six research checks per US trading day, and use SQLite for execution records and recovery.

The user accepts experiment costs but did not specify new capital or risk figures. Existing paper limits remain 20 USDT capital, 10% maximum position, 0.5% single-trade risk and 2% daily risk. The v0.1 stop/fill document is not approved.

## Delivered

The default API checker uses Stocks rule, quote and open-order endpoints plus separate Spot-account and API-permission diagnostics. The read-only runner loads startup files, checks due slots and records results. SQLite, unique run IDs, a process lock, unfinished-run blocking and deterministic export recovery are implemented. Both schedule translations contain 42 provisional checks. Sixteen automated tests passed. API instructions, the stop/fill proposal, review, setup instructions and this handoff are saved locally.

## Actual Verification

Latest saved call: 2026-09-14 06:35:31 UTC / 15:35:31 Asia/Tokyo, run `manual_20260914T153531531996`. Public connectivity passed and credentials were present. Spot account returned HTTP 401 / Binance -2015; stock rules, quotes, open orders and API permissions returned HTTP 400 / Binance -2015. Account access and stock eligibility are unverified. Paper cash is 20 USDT with no positions. No order was proposed, submitted or filled. Real holdings and cash were not reconciled.

Evidence: [API result](../05-交易记录-data/证据资料-evidence/manual_20260914T153531531996.json), [journal](../05-交易记录-data/运行日志-journal/manual_20260914T153531531996.md), [readiness](../04-运行状态-state/readiness.json). The error does not distinguish an invalid key from an IP or permission problem.

## Corrections and Remaining Gaps

Earlier Spot-only checks and SPYUSDT probes did not establish whether Binance Stocks APIs exist. The implementation now uses `/sapi/v1/equity/` and equity tickers such as AAPL. Ordinary stocks, bStocks, crypto Spot and Spot testnet are different scopes; do not silently switch between them. The reference PDF remains unchanged. Future ordinary-equity execution should explicitly disable tokenization; there is no order implementation now.

Authentication, eligibility, equity holdings/settlement cash and quote freshness remain unverified. The 5-second sampling, 15-second gap threshold, 30-minute reassessment and 1.5-times net-risk target are proposed settings only. The fill engine and continuous risk monitor do not exist yet. SQLite tracks runs, not a complete trading ledger. `local_paper_ledger_initialized=true` refers to the original initial-capital/empty-position state, not a tested fill engine. The original strategy's local-paper-versus-Binance-eligibility conflict remains pending resolution after mode and draft review.

## Scheduling

Provisional sessions: September 14-18 and 21-22, 2026. Six America/Chicago times: 07:45, 09:30, 11:00, 13:00, 14:15, 14:45. A timezone-specific configuration card was rendered; saving/activation has not been verified. No active scheduler is claimed. Experiment start/end remain null and day index remains zero. If setup is delayed, validate and rebase all seven sessions; never fabricate missed history.

## Next Steps

1. Check the local production HMAC key pair, read permissions and IP allowlist in Binance.
2. Repeat read-only Stocks checks and record actual results. Do not manually mark readiness as passed.
3. Review the stop/fill proposal, choose data and fee treatment, then implement it.
4. Verify fills, duplicate prevention, restart recovery, data gaps and scheduling before synchronizing active rules in both languages.
5. Rebase session dates if necessary, save and activate research scheduling. Validate continuous monitoring separately. Live orders still require specific authorization.

## Maintenance

Readiness owns verification facts, current-state owns paper portfolio state, and SQLite owns read-only run records. Generated API journals are deterministic exports; research belongs in separate `-research` files. Drafts remain drafts until approved. Earlier Documents-project credentials and history were not merged. This organization pass preserved existing paths, credentials, the PDF and bilingual material, and did not call Binance, enable a task or change funds.
