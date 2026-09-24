# 7 天股票交易实验

这是一个使用 **10000 USDT 虚拟资金** 的 7 个美股交易日实验。系统可以在风险规则内自主进行本地 paper trading，但不会提交真实 Binance 订单，也不能被描述为稳定盈利系统。

## 先看这里

1. [开始使用](01-开始使用-getting-started/开始使用.md)
2. [当前项目说明](01-开始使用-getting-started/项目完整说明.md)
3. [中文交易策略](02-项目文档-docs/TRADING-STRATEGY.zh-CN.md)
4. [当前组合状态](05-交易记录-data/current-state.json)
5. [最新交易日志](05-交易记录-data/运行日志-journal/)

## 中文目录

| 目录 | 给谁看 | 作用 |
| --- | --- | --- |
| `01-开始使用-getting-started` | 所有人 | 操作步骤、项目总览和英文说明 |
| `02-项目文档-docs` | 研究者 | 策略、Binance 接口、安全边界、部署和变更记录 |
| `03-定时任务-routines` | 运行维护者 | 六次检查日程、连续性规则、自动任务提示词和任务状态 |
| `04-运行状态-state` | 系统 | readiness 安全开关、paper 参数和运行锁 |
| `05-交易记录-data` | 复盘者 | 当前组合、模拟账本、决策、日志和证据 |
| `06-程序脚本-scripts` | 开发者 | 只读连接、调度器和 paper trading 引擎 |
| `07-自动测试-tests` | 开发者 | 安全边界、账本、调度和恢复测试 |
| `08-参考资料-references` | 研究者 | 原始 PDF 等参考材料，不作为当前运行指令 |
| `10-API密钥-仅本地-local-secrets` | 账户所有者 | 本地 API 配置；真实密钥禁止提交或分享 |

根目录的 `AGENTS.md` 和 `AGENTS.zh-CN.md` 是 AI 必读运行规则，不能移入其他目录。`.github/` 保存 GitHub Actions 工作流。

## 当前安全边界

- 只允许 paper trading。
- `live_trading_enabled` 必须保持 `false`。
- API 仅用于读取账户、订单和股票行情。
- 不交易期权、期货、杠杆、保证金、垃圾股或不明确产品。
- 每次决策都必须保存理由、证据、风险和结果。
- 行情不清楚、数据不足或定时检查错过时，保持空仓。

## 常用命令

```bash
cd "/Users/a123/Desktop/7天股票交易实验"

# 检查 Binance 只读连接
python3 -B "06-程序脚本-scripts/binance_readiness_check.py" --update-readiness

# 查看当前是否到达计划检查时点
python3 -B "06-程序脚本-scripts/run_observation.py" --dry-run

# 运行全部安全测试
python3 -B -m unittest discover -s "07-自动测试-tests" -v
```

真实 API Key 只保存在 `10-API密钥-仅本地-local-secrets/binance-api.env`。不要把密钥粘贴到聊天、日志、截图或 GitHub 文件中。
