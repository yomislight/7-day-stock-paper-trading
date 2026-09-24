# 币安股票 API 接入说明

正式地址：https://api.binance.com。本地 HMAC 密钥统一读取根目录 10-API密钥-仅本地-local-secrets/binance-api.env。检查脚本默认使用股票接口，--spot-only 仅用于现货账户诊断。

| 用途 | GET 路径 | 认证方式 |
| --- | --- | --- |
| 校准时间 | /api/v3/time | 公共 |
| 现货账户诊断 | /api/v3/account | 签名 |
| API 权限 | /sapi/v1/account/apiRestrictions | 签名 |
| 股票交易规则 | /sapi/v1/equity/market/exchangeInfo?symbol=AAPL | API Key |
| 股票报价 | /sapi/v1/equity/market/quote?symbol=AAPL | API Key |
| 股票未完成订单 | /sapi/v1/equity/order/open-orders | 签名 |

脚本只实现 GET 请求，分别记录各项读取是否成功。报价可读取不等于报价已验证新鲜，也不等于地区资格或交易权限已通过。Spot 测试网不能证明存在股票测试网，目前没有配置经过验证的股票模拟服务。

原始 Alpaca PDF 保留为参考。本文件及英文版是针对当前项目编写的币安适配说明。股票使用 AAPL 等代码，不使用 SPYUSDT；未来若实现普通股票执行，应显式设置 tokenize=false。本次没有下单实现。

错误 -2015 表示密钥、IP 或权限被拒绝。请核对本地 Key/Secret 是否属于同一组 Binance.com 正式环境 HMAC 密钥、读取权限是否开启、IP 白名单是否匹配。不要绕过地区限制或让脚本自动接受账户协议。日志不输出原始账户响应、余额、密钥或签名。

在项目目录运行 `python3 -B 06-程序脚本-scripts/binance_readiness_check.py --update-readiness`。退出码 0 表示请求范围检查通过，2 表示凭证或账户/股票权限未通过，3 表示公共网络失败，4 表示本地文件需检查。空报价或空标的列表不能算股票接入成功。

依据：[行情](https://developers.binance.com/en/docs/catalog/advanced-trading-stocks-trading/api/rest-api/market-data)、[股票订单](https://developers.binance.com/en/docs/catalog/advanced-trading-stocks-trading/api/rest-api/trade)、[API 权限](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account)。
