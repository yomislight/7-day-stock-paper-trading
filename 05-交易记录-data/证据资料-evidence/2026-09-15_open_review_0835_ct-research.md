# 2026-09-15 08:35 Central 开盘后研究证据

- 记录时间：2026-09-15T13:38:00Z / 2026-09-15 08:38 Central。
- 执行范围：仅本地 paper trading；未发送真实 Binance 订单。
- Binance Stocks 只读检查：账户、权限、股票规则、报价和未结订单读取均通过，错误为空；真实订单权限保持关闭。

## 即时报价

以下为 Binance Stocks 最新买一/卖一，只用于本地模拟判断：

| 标的 | 买一 | 卖一 | 点差 | 与 9 月 14 日收盘的粗略比较 |
| --- | ---: | ---: | ---: | --- |
| SPY | 759.59 | 759.62 | 0.03 | 低于 760.88，约 -0.17% |
| QQQ | 708.69 | 708.71 | 0.02 | 高于已检索到的 705.97，约 +0.39% |
| AAPL | 330.51 | 330.58 | 0.07 | 低于 333.08，约 -0.75% |
| NVDA | 213.07 | 213.12 | 0.05 | 高于 210.96，约 +1.00% |
| XOM | 166.92 | 167.00 | 0.08 | 高于 165.08，约 +1.14% |

## 市场背景

- AP 盘前报道：股指期货偏弱，油价和美债收益率上升；10 年期美债收益率约 5.01%，宏观环境对成长股估值不利。
- 美联储官方日历：9 月 15 至 16 日为 FOMC 会议窗口，政策事件风险仍未解除。
- 开盘首几分钟内部走势分化：SPY、AAPL 偏弱，而 QQQ、NVDA、XOM 偏强，尚未形成统一的风险方向。
- Binance Stocks 当前只提供最新买卖报价，本轮没有可靠的开盘成交量、VWAP 或完整日内区间数据，不能确认突破质量。

## 决策

- 本轮不交易。
- 原因：虽然 XOM 和 NVDA 相对强、点差较窄，但当前刚开盘，缺少成交量确认；宽基与个股方向分化，同时油价、收益率与 FOMC 事件风险叠加，不足以定义保守且可复核的入场、结构止损和目标。
- 反方风险：继续等待可能错过早盘延续，但避免在信息最嘈杂的开盘阶段追价更符合当前策略。
- 下一步：11:00 Central 重新比较 SPY/QQQ 方向、AAPL/NVDA/XOM 相对强弱、点差和可取得的成交量证据；该时点为最后一次考虑新 paper 仓位的计划窗口。

## 来源

- Binance Stocks 最新报价与只读状态：`05-交易记录-data/证据资料-evidence/2026-09-15_open_review_0835_ct.json`
- AP 市场报道：https://apnews.com/article/123ddc2d8ba06c324cbbd899f7eeebd2
- Federal Reserve 2026 年 9 月日历：https://www.federalreserve.gov/newsevents/2026-september.htm
- 历史参考：SPY https://twelvedata.com/markets/568728/etf/nyse/spy/historical-data
- 历史参考：AAPL https://kxlt.marketminute.com/quote/NQ%3AAAPL/historical
- 历史参考：NVDA https://www.financecharts.com/compare/NVDA/summary/price
- 历史参考：XOM https://www.financecharts.com/stocks/XOM/summary/price
