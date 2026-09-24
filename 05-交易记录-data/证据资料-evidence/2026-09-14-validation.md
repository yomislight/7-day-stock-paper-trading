# 验证记录 / Validation Record

日期 / Date: 2026-09-14。整理阶段仅做本地验证，未重新调用币安账户。本文件是历史证据，不是实时 readiness。

## 自动测试 / Automated Tests

命令：`python3 -B -m unittest discover -s tests -v`，在项目根目录运行。16 项通过，覆盖：配置格式、密钥缺失、错误信息脱敏、重定向阻止、股票接口映射、空标的与无效报价、权限分离、状态保留、重复和未完成运行、双连接竞争、导出恢复、42 个研究时点及中英文一致性。

These are offline tests, including mocked API responses. They do not prove that actual Binance credentials or account permissions work.

## 整理检查 / Organization Checks

本次整理后重新运行，16 项测试全部通过。另检查了 45 个本地 Markdown 链接，无失效链接；6 个 JSON 文件均可解析；SQLite 只读完整性检查返回 ok，已完成运行记录 1 条。未读取或复制凭证和编辑器交换文件的内容，Git 忽略规则已补充交换文件及备份类型。

## 真实接口 / Actual API Evidence

最近保存的调用：2026-09-14T06:35:31.533113+00:00。公共接口可达，凭证存在；账户、股票和 API 权限查询均返回 Binance -2015。

见 [API 结果](manual_20260914T153531531996.json) 和 [只读运行日志](../journal/manual_20260914T153531531996.md)。数据库、日志、证据和 current-state 已完成端到端保存，导出恢复演练成功。

Authenticated access has not passed. No order was proposed, submitted or filled.

## 日程 / Scheduling

七个预备交易日共 42 个研究时点通过离线检查；真实自动任务未核验保存或执行。见 [自动任务状态](../../03-定时任务-routines/automation-status.json)。

## 尚未验收 / Not Yet Validated

真实账户认证、股票交易资格、行情新鲜度、股票持仓与结算现金、模拟成交引擎、连续风险监控，以及真实定时唤醒。止损草案仍待用户审阅。

Initial paper capital and current cash remain 20 USDT with no positions. This record does not activate the draft, change risk limits or start the experiment.
