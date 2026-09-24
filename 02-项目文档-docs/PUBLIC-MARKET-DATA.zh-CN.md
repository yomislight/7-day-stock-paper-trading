# 无密钥辅助量价数据

## 当前方案

本实验不再要求 Alpaca 账户。日本居民无法按真实信息完成当前 Alpaca 券商开户流程时，不应填写虚假的美国地址、电话、税务居住地或税号。

运行时使用两个互相独立的只读来源：

- Binance Stocks：验证标的、交易规则、最新买卖报价，并作为本地模拟成交价格。
- Yahoo Finance 公共图表端点：补充五分钟 OHLCV、当日累计成交量、近期平均成交量和推导 VWAP。

Yahoo 图表端点不需要账户或 API Key，但它不是项目可控制的正式付费数据合同，字段和可用性可能变化。因此它只用于 paper trading 研究，不得用于真实资金订单，也不得描述成官方 SIP 全市场行情。

## 推导指标

脚本按五分钟 K 线计算：

- 当日累计成交量。
- 最近最多 20 个交易日的平均成交量。
- 当前成交量速度与历史平均速度之比。
- 使用 `(最高价 + 最低价 + 收盘价) / 3` 乘以成交量得到的推导 VWAP。

这里的 VWAP 是五分钟聚合数据推导值，不是交易所发布的逐笔成交 VWAP。

## 开仓门槛

新开模拟仓位必须同时满足：

1. Binance 股票规则、权限和最新买卖报价验证通过。
2. 目标标的存在当前纽约交易日的五分钟 K 线和正成交量。
3. 最新五分钟 K 线不超过 20 分钟。
4. 至少有 10 个历史交易日可用于成交量背景。
5. 新闻、市场结构或事件证据还提供至少一个独立证据类别。

辅助数据失败只会禁止新开仓，绝不能阻止止损、减仓或收盘清仓。

## 本机检查

```bash
python3 -B 06-程序脚本-scripts/public_market_data_check.py --symbols AAPL --update-readiness
```

只有正常交易时段出现 `market_data_ready: true` 才表示量价门槛通过。盘前、收盘后或休市时显示 `false` 属于正常的安全行为。

## 数据依据

- [Binance Stocks Market Data](https://developers.binance.com/en/docs/catalog/advanced-trading-stocks-trading/api/rest-api/market-data)
- [Yahoo Finance](https://finance.yahoo.com/)
