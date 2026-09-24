# AI 股票交易实验运行规则

本项目是一个为期 7 个交易日的股票/ETF 研究与 paper trading 实验。
它不是实盘交易系统，也不能被描述为稳定盈利系统。

## 安全默认值

- 默认只能使用 paper trading。
- 除非用户在聊天中明确授权某一笔具体实盘订单，否则实盘交易保持关闭。
- 未经人工确认，绝不提交真实资金订单。
- 如果任何 readiness 检查缺失、为 false、过期或含义不清，禁止下单。
- 如果市场条件不清楚，优先观察，不交易。
- 风险控制优先于收益。

## 平台范围

- 目标平台：Binance 股票/ETF交易能力。
- 使用任何执行路径前，必须先验证 Binance 账户权限、地区资格、API 支持，以及是否存在 paper/sandbox 能力。
- 如果 Binance 不提供股票/ETF paper trading，则使用本项目的本地 paper ledger 进行模拟记录。
- Binance API key 统一保存在项目根目录的 `10-API密钥-仅本地-local-secrets/binance-api.env`，只读检查脚本只读取此文件。不要要求用户把密钥粘贴到聊天窗口；分享项目时使用 `10-API密钥-仅本地-local-secrets/binance-api.env.example`，不要分享已填写的凭证文件。
- Binance 用于股票规则和最终可执行报价；无密钥公共图表源只为 paper research 补充五分钟 K 线、成交量背景与推导 VWAP。补充数据缺失、过期或不完整时禁止新开模拟仓位，但不得因此阻止止损或减险。公共图表数据不得描述成官方 SIP 全市场合并数据。

## 允许做的事

- 读取策略、日程、状态、日志和证据文件。
- 在本地已有凭证时，执行只读的账户、持仓、订单和市场数据检查。
- 生成观察列表、风险备注和 paper trade 记录。
- 仅在 paper trading 范围内，按照策略和风险限制自主决定买入、卖出、减仓、止损、清仓、继续持有或空仓。
- 只有 `readiness.json` 中 `autonomous_paper_execution_enabled: true` 时才允许自动纸面执行；执行只能通过 `06-程序脚本-scripts/paper_engine.py` 写入本地账本。
- 记录“不交易”的决定、证据和理由。

## 禁止做的事

- 没有明确人工确认，禁止提交实盘订单。
- 禁止交易期权、期货、保证金、杠杆产品、加密永续、低流动性股票、低价垃圾股或不明确证券化产品。
- 禁止只根据单条新闻或单个指标下单。
- 禁止满仓、重仓或使用全部资金。
- 禁止把凭证写入日志、证据文件、命令输出或聊天内容。
- Paper trading 自主决策不授权实盘交易、真实订单、转账、修改账户设置或开启交易权限。

## 每次启动必须先读取

每个定时任务开始前必须读取：

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
- `05-交易记录-data/运行日志-journal/` 中最新记录，如果存在

## 每次结束必须更新

每个定时任务结束时必须更新：

- `05-交易记录-data/current-state.json`
- `05-交易记录-data/运行日志-journal/` 中当天交易日志
- `05-交易记录-data/证据资料-evidence/` 中的证据说明
- `09-每日中文报告-daily-reports/` 中当天的中文交易日报

每条日志必须写清：

- 本次做了什么
- 为什么这么做
- 有没有提出订单
- 有没有提交订单
- 有没有成交
- 当前持仓
- 当前现金
- 当前风险
- 下一次任务重点
- 是否需要人工确认

## 币安运行入口

- 股票接口映射见 `02-项目文档-docs/BINANCE-API.zh-CN.md` 及英文版。默认检查 `/sapi/v1/equity/`，不通过 Spot 交易对猜测股票能力。
- `06-程序脚本-scripts/run_observation.py` 只读。`06-程序脚本-scripts/paper_engine.py` 只可模拟本地纸面成交，不包含任何券商 POST 路径。
- 本地纸面规则强制：同时一个仓位、单仓 10%、单笔计划风险 0.5%、至少两类证据、净风险收益比至少 1.5、Central 11:30 后不开新仓、禁止隔夜。
- 中英文均保留。第二轮日期以中英文 schedule 为准；配置日、手动检查、漏跑时点和事后补写报告都不能计为已完成交易日。
