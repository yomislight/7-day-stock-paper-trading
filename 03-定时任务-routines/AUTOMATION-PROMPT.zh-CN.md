# 定时任务说明与保存文案

本文件是当前 GPT heartbeat 的仓库内说明副本。实际部署状态见 [automation-status.json](automation-status.json)。

## 当前安排

项目目录为 `/Users/a123/Desktop/7天股票交易实验`，任务返回当前实验会话。America/Chicago 时间每日 07:45、08:35、11:00、13:00、14:15、14:45；第二轮七天日期见 [schedule.json](schedule.json) 及 [中文版](schedule.zh-CN.json)，共 42 个时点，迟到容差 30 分钟。六个时点分别使用独立 GPT heartbeat，本机 launchd 每 5 分钟提供只读兜底；GitHub 托管 Runner 仍受 Binance HTTP 451 限制。

## 任务文案

所有项目操作仅在本桌面目录进行。每次读取中英文 AGENTS、策略、schedule、CONTINUITY、readiness、current-state 和最新 journal。

所有给用户阅读的报告必须使用中文。每次任务结束后，运行中文日报生成器，把当天资金、持仓、模拟买卖、盈亏、不交易原因、风险和下一步汇总到 `09-每日中文报告-daily-reports/YYYY-MM-DD-每日交易报告.md`。结构化决策必须增加 `reason_zh`，用简明中文说明原因；存在数据缺口时增加 `data_gap_zh`。收盘任务必须在 `05-交易记录-data/证据资料-evidence/YYYY-MM-DD-market-summary.zh-CN.json` 保存可核验的大盘复盘，包括主要指数涨跌与收盘点位、利率、油价、市场主线、板块结构、对交易决策的影响、下一交易日重点和来源链接。中文日报必须分别回答为什么买入或没有买入、为什么卖出或没有卖出，并区分主动市场判断与漏跑、延迟、数据缺失等执行问题。每天附复盘和需要共同修改的事项，不得把漏跑描述成正确的不交易决策。

先运行 `python3 -B 06-程序脚本-scripts/run_observation.py --dry-run`；不在预定七个美股交易日和研究时点 30 分钟容差内则报告本次没有合法执行窗口，绝不补造交易。有效时点运行 `python3 -B 06-程序脚本-scripts/run_observation.py`。若返回 `duplicate_skipped`，说明本机兜底已保存只读证据，应继续完成研究、paper 决策和报告；若返回 `another_run_active`，等待该运行结束后核对证据。中断运行须先用恢复流程核对。

随后按该时点主题查询官方日历、新闻和可验证行情，将研究另存为以同一 run_id 命名并加 `-research` 后缀的日志和证据，更新下一任务重点，不修改自动导出的 API 检查日志。

研究完成后，独立决定本地 paper ledger 应开仓、管理、平仓还是不交易。用户仅授权自动 paper trading；绝不提交真实 Binance 订单、转账、代币化请求或账户设置修改。

每次决策在 `05-交易记录-data/决策记录-decisions/` 新建不含密钥的 JSON，必须有 `paper_trading_only: true`，`action` 只能为 `open_long`、`manage`、`close` 或 `no_trade`；开仓时必须写入证据、逻辑、止损和目标。随后运行 `python3 -B 06-程序脚本-scripts/paper_engine.py --decision <file> --run-id <date_slot>_paper`；`_paper` 后缀可防止覆盖只读运行器生成的证据文件。引擎会刷新只读 Stocks 行情，拒绝过期或不安全状态，并且只写入本地 paper ledger。只有 08:35 与 11:00 Central 可考虑新开仓；13:00 只管理风险；14:15 必须清掉没有明确隔夜许可的纸面仓位。

保持 10000 USDT 模拟资金及既有风险上限；费用、流动性、数据质量或证据不满足时必须记不交易。此任务不承担连续止损职责。密钥只由脚本在本机读取，禁止输出。

未变化或不可行动时保持安静；计划报告、重大变化、完成、失败或需要用户处理时发送通知。若实际开始日期延后，重新核验七个交易日并同步中英文日程。七天结束后暂停本任务。

## 验证边界

已离线核对第二轮 42 个时点和中英文时间一致性。第一轮只有 6 个计划时点完成，不能计为跑满 7 天。第二轮必须用 `experiment_status.py` 验收；只有 7 天均完成六次只读检查、六次 paper 决策、中文日报和收盘复盘，才算完成。
