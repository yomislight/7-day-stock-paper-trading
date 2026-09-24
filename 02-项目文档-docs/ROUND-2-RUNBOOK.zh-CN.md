# 第二轮 7 天实验运行说明

## 日期

第二轮按 America/Chicago 时区运行：

- 2026-09-24
- 2026-09-25
- 2026-09-28
- 2026-09-29
- 2026-09-30
- 2026-10-01
- 2026-10-02

每天固定 07:45、08:35、11:00、13:00、14:15、14:45 六个时点。

## 三层执行

1. GPT 定时任务：研究、决策、运行 paper engine、写中文日报并推送到当前 GPT 对话。
2. 本机 launchd 兜底：每 5 分钟检查一次，仅在合法时点执行 Binance 与补充行情的只读检查。
3. GitHub Actions：保留代码测试与异地审计；由于托管 Runner 访问 Binance 曾返回 HTTP 451，不作为本轮主执行器。

## 本机只读兜底权限

后台 Python 首次读取桌面目录时，macOS 可能显示 `Operation not permitted`。这是系统隐私权限，不是普通文件读写权限。处理方式：

1. 打开“系统设置 -> 隐私与安全性 -> 完全磁盘访问权限”。
2. 点加号，将 `/Applications/Xcode.app/Contents/Developer/usr/bin/python3` 加入并开启。
3. 重新加载只读兜底：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yomi.seven-day-trading-observer.plist
```

若系统仍拒绝访问，不要反复重试或移动密钥；保持六个 GPT 定时任务运行，并在日报中记录本机兜底未启用。

防休眠任务使用 `caffeinate -i -s`。它允许显示器熄屏，同时防止空闲导致的系统睡眠；关机、合盖硬件睡眠、断电或断网仍会中断任务。

## 怎样判断跑满

```bash
cd "/Users/a123/Desktop/7天股票交易实验"
python3 -B 06-程序脚本-scripts/experiment_status.py
```

必须看到：

- `fully_completed_trading_days: 7`
- `experiment_complete: true`

任何漏跑都必须在当日报告中单独记录，不能通过事后补造交易来变成“完整”。
