# 7 Day Conservative Stock/ETF Paper Trading Strategy

## Purpose

Run a controlled 7 U.S. trading day experiment to test whether AI-assisted research can manage a small, explainable paper portfolio using news, market data, price action, and volume. The goal is process quality, traceability, and risk discipline, not proof of profitability.

## Capital And Mode

- Starting capital: 10000 USDT equivalent.
- Default execution: paper trading only.
- Live trading: disabled unless explicitly authorized by the user for a specific order.
- Accounting currency: USDT for experiment tracking; convert to USD equivalent when market data or stock trading requires USD/USDC notation.

## Paper Trading Autonomy

Within paper trading only, the AI may independently decide to buy, sell, reduce, stop out, flatten, hold, or stay in cash. The user does not need to approve each paper trade.

This autonomy applies only to the local paper ledger. It does not authorize live orders, real-money execution, transfers, account setting changes, or enabling trading permissions. Every autonomous paper decision must still satisfy the strategy, readiness, evidence, position sizing, stop loss, and daily loss rules.

## Tradable Assets

Only consider highly liquid U.S.-listed stocks or ETFs available through the user's eligible Binance stock/ETF access.

Preferred universe:

- Broad ETFs: SPY, QQQ, DIA, IWM, VOO, IVV
- Mega-cap liquid stocks: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, JPM, XOM, UNH
- Other stocks only if they have high average daily dollar volume, tight spreads, clear news context, and are supported by the platform.

## Prohibited Assets

Do not trade:

- Options
- Futures
- Margin or leveraged positions
- Leveraged ETFs, inverse ETFs, or 2x/3x products
- Low-liquidity stocks
- Penny stocks or highly speculative microcaps
- Crypto, perpetuals, or tokenized securities not clearly approved for this experiment
- Any product whose legal status, region eligibility, settlement, fees, or underlying exposure is unclear

## Entry Conditions

A paper trade may be considered only when all required conditions are met:

- `04-运行状态-state/readiness.json` allows paper trading and does not allow live trading.
- Asset is in the permitted universe and is supported by Binance stock/ETF access or the local paper ledger.
- A fresh Binance executable quote and fresh read-only public five-minute volume/derived-VWAP evidence are both available. The public bars are contextual research data, not official consolidated SIP data, and the derived VWAP is not an exchange-published VWAP.
- At least two independent evidence categories support the trade idea, such as:
  - Market trend or sector context
  - Price action relative to prior range, VWAP, moving average, or support/resistance
  - Volume confirmation compared with recent average
  - Relevant news, earnings, macro release, or official announcement
- The trade has a defined entry, stop, exit target or exit condition, and maximum loss.
- Position size stays within the risk limits below.
- The reason to avoid the trade has been considered and recorded.

Do not enter if the decision relies on only one headline, one social post, one indicator, or an unverified quote.

## Exit Conditions

Exit a paper position when any of the following occurs:

- Stop loss is reached.
- The original trade thesis is invalidated.
- Price fails to follow through after entry and risk/reward deteriorates.
- A scheduled risk reduction window begins.
- The position is not explicitly allowed to remain overnight.
- Daily loss limit is reached.
- Market data, account data, or execution status becomes unreliable.

## Stop Loss Rules

- Every paper trade must have a stop level before entry.
- Maximum planned loss per trade: 0.5% of starting capital.
- With 10000 USDT starting capital, maximum planned single-trade loss is 50 USDT equivalent.
- If this loss limit makes a position impractically small, do not trade.
- Stops must be based on both price structure and risk budget, not only an arbitrary percentage.

## Position Sizing

- Maximum position size: 10% of starting capital per position.
- With 10000 USDT starting capital, maximum position notional is 1000 USDT equivalent.
- Prefer one active position at a time.
- Never use the full account.
- Do not average down.
- Do not increase exposure after 1:00 p.m. Central.

## Daily Loss Limit

- Maximum daily loss: 2% of starting capital.
- With 10000 USDT starting capital, maximum daily loss is 200 USDT equivalent.
- If realized plus open risk reaches this limit, stop trading for the day and record a risk stop.

## Single Trade Loss Limit

- Maximum single-trade loss: 0.5% of starting capital.
- With 10000 USDT starting capital, maximum single-trade loss is 50 USDT equivalent.
- If fees, spreads, or minimum order size make this impossible, the system must observe only.

## Overnight Policy

Default: close intraday paper positions before the end of the session.

Overnight holding is allowed only when all are true:

- The strategy file is updated with a specific overnight thesis.
- The asset is a high-liquidity stock or ETF.
- Event risk is known and acceptable.
- Position size is small enough to survive a gap without breaching the daily loss limit.
- The journal explains why holding overnight is safer than exiting.

## Must Stop Trading

Stop all trading and switch to observation when:

- `readiness.json` is missing, malformed, or has unsafe values.
- Live trading appears enabled unexpectedly.
- Human confirmation would be needed for a real order and has not been obtained.
- Account, order, position, or market data cannot be reconciled.
- Daily loss limit is reached.
- Two consecutive paper trades hit planned stops on the same day.
- News or market conditions are chaotic, contradictory, or impossible to verify.
- The platform product type is unclear.
- The scheduler misses a critical risk-management check while positions are open.

## Observation Only

Only observe and record when:

- Binance stock/ETF eligibility or API capability is not verified.
- Paper trading capability is not verified and the local paper ledger is not initialized.
- Market is closed, halted, or abnormal.
- Spreads are wide relative to the trade risk.
- Volume is insufficient.
- Price is moving too quickly to define a controlled stop.
- The trade requires more than 10% position size to be meaningful.
- The likely loss including spread and fees exceeds 50 USDT equivalent.
- Evidence is incomplete or relies on one source.

## Evidence Requirements

For every proposed trade or no-trade decision, save:

- Timestamp and market session
- Asset symbol
- Current price and source
- Volume context
- News or event links
- Entry/exit/stop levels if applicable
- Risk calculation
- Final decision and reason
