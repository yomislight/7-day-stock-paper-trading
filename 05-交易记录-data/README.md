# 05 交易记录

- `../09-每日中文报告-daily-reports/`：给人直接阅读的每日交易结果。优先看这里，不需要理解 JSON 或数据库。
- `current-state.json`：当前现金、权益、持仓、盈亏和下一次任务重点。
- `paper-ledger.json`：本地模拟成交事件账本。
- `决策记录-decisions/`：每次 AI 的非秘密结构化决策。
- `运行日志-journal/`：按日期和任务保存的人类可读运行日志。
- `证据资料-evidence/`：行情快照、新闻链接、只读检查结果和决策证据。
- `runs.sqlite3`：只读调度器数据库，已被 Git 忽略。

日常查看时打开 `../09-每日中文报告-daily-reports/`。需要深入复盘时，再看 `current-state.json`、`运行日志-journal/` 与对应的 `证据资料-evidence/`。
