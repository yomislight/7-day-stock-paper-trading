# 09 API 密钥，仅限本地

1. 使用 HMAC 类型 Binance API Key。
2. 只开启读取权限。
3. 不开启现货交易、保证金、合约、转账或提现权限。
4. 将空白模板 `binance-api.env.example` 复制为 `binance-api.env` 后在本机填写。
5. 不要把真实 Key 或 Secret 发到聊天、截图、日志或 GitHub。

`binance-api.env` 已被 Git 忽略。空白模板可以提交，真实配置绝不能提交。

## 补充股票盘中数据

Binance 股票行情没有提供本实验所需的分钟成交量和 VWAP。当前运行器改用无密钥公共五分钟图表数据，不再要求 Alpaca 凭证。旧的 `alpaca-market-data.env` 即使仍保存在本机，也不会被运行器读取，并继续受 Git 忽略规则保护。

详细边界见 `02-项目文档-docs/PUBLIC-MARKET-DATA.zh-CN.md`。
