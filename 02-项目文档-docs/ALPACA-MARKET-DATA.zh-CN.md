# Alpaca 行情方案已停用

## 状态

本项目运行时已不再调用 Alpaca，也不要求填写 Alpaca API Key。

2026-09-24 验证时发现，日本居民无法按真实资料完成当前 Alpaca 券商开户流程。项目不得要求用户填写虚假的美国地址、电话、税务居住地或税号，也不应为了本次 7 天 paper trading 实验购买付费行情套餐。

当前替代方案见[无密钥辅助量价数据](PUBLIC-MARKET-DATA.zh-CN.md)：Binance 提供股票规则和最终模拟成交报价，公共五分钟图表数据只用于量价研究。数据不完整时禁止新开仓。

旧的本地 `alpaca-market-data.env` 仍受 `.gitignore` 保护，但运行器不会读取它，也不会把它上传到 GitHub。
