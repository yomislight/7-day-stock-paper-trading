# GitHub Actions 云端运行说明

## 安全边界

- 仓库中不保存任何真实 API Key 或 Secret Key。
- `10-API密钥-仅本地-local-secrets/binance-api.env` 只用于本地，不会被 Git 提交，也不会作为 artifact 上传。
- GitHub Actions 只从仓库的 Actions Secrets 读取凭据，并在运行期间创建权限为仅当前用户可读的临时文件。
- 运行结束后删除临时文件。
- 当前脚本只做 Binance 股票接口读取与本地 paper trading 记录，不提交真实订单。
- API Key 应只开启读取权限。不要开启提现、转账、合约、杠杆或现货/股票交易权限。

## 需要填写的 GitHub Secrets

打开 GitHub 仓库：`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`。

创建以下 Secrets，值在 GitHub 页面填写，不要写进项目文件或聊天窗口：

```text
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_ENV=
```

`BINANCE_ENV` 填 `production`。这里的 production 只表示读取 Binance 正式账户接口，不代表允许真实交易。

手机 Telegram 推送是可选项。如需使用，再创建：

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## 定时安排

工作流按照 2026 年 9 月美国中部夏令时运行，每个交易日最多六次：

| Central 时间 | UTC cron | 任务 |
| --- | --- | --- |
| 07:45 | 12:45 | 盘前研究与 readiness |
| 08:35 | 13:35 | 开盘后机会检查 |
| 11:00 | 16:00 | 持仓与最后新开仓检查 |
| 13:00 | 18:00 | 仅风险管理 |
| 14:15 | 19:15 | 准备清理日内仓位 |
| 14:45 | 19:45 | 收盘前核对与记录 |

`03-定时任务-routines/schedule.json` 仍是日期和时段的最终约束。即使 GitHub cron 在其他工作日触发，Python 运行器也会在实验日期或允许窗口之外直接跳过。

## 第一次运行

1. 把整个项目推送到一个私有 GitHub 仓库。
2. 在仓库中填写上述 Actions Secrets。
3. 打开 `Actions` -> `7-day paper trading observation` -> `Run workflow`。
4. 查看任务摘要，并下载 `paper-trading-record-*` artifact 核对运行记录。

## 重要限制

GitHub 托管 Runner 的公网 IP 不固定。如果 Binance API Key 启用了固定 IP 白名单，接口可能返回 `-2015`。若必须固定 IP，应迁移到有固定出口 IP 的 VPS 或自托管 Runner。

2026-09-15 的首次 GitHub 托管 Runner 实测中，Binance 公开 `ping` 和时间接口均返回 HTTP 451。该结果说明托管 Runner 的运行地区无法访问 Binance.com，不是 API Key 验证失败。当前工作流已经部署，但不能依靠 GitHub 托管 Runner完成 Binance 数据读取。推荐在允许访问 Binance 的地区使用带固定出口 IP 的 VPS，并注册为带 `binance-paper` 标签的 GitHub 自托管 Runner。

目前 `06-程序脚本-scripts/run_observation.py` 是只读观察运行器，不包含自动生成 paper 买卖指令、成交撮合或盈亏更新逻辑。它可以验证连接并留下记录，但还不能独立完成七天自主 paper trading；这部分需要下一阶段补齐并测试。
