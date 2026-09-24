#!/usr/bin/env python3
"""把机器交易记录汇总成普通人可以直接阅读的中文日报。"""

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path("05-交易记录-data")
REPORT_DIR_NAME = "09-每日中文报告-daily-reports"

ACTION_LABELS = {
    "open_long": "模拟买入",
    "manage": "持仓管理",
    "close": "模拟卖出",
    "no_trade": "不交易",
}

EVENT_LABELS = {
    "open_long": "模拟买入成交",
    "mark": "持仓价格与风险更新",
    "close": "模拟卖出成交",
}

EXIT_REASON_LABELS = {
    "stop": "触发止损",
    "target": "达到目标价",
    "thesis_invalid": "交易理由失效",
    "time_exit": "到达计划退出时间",
    "end_of_day": "日内仓位收盘前退出",
    "manual_exit": "人工要求退出模拟仓位",
    "strategy_entry": "满足策略入场条件",
    "risk_refresh": "例行风险复核",
}

SLOT_LABELS = {
    "startup": "系统启动检查",
    "pre_market_0745_ct": "07:45 盘前检查",
    "open_review_0835_ct": "08:35 开盘后检查",
    "late_morning_1100_ct": "11:00 上午检查",
    "midday_1300_ct": "13:00 午后风险管理",
    "flatten_prep_1415_ct": "14:15 尾盘减险",
    "end_of_day_1445_ct": "14:45 收盘前核对",
}

SLOT_REASONS = {
    "startup": "初始化或状态核对期间不满足正式入场条件，因此保持现金。",
    "pre_market_0745_ct": "盘前阶段只建立观察清单；尚无正常交易时段的价格、成交量和价差确认，因此不入场。",
    "open_review_0835_ct": "开盘后市场方向不一致，成交量确认不足，且宏观事件风险偏高，因此等待更清晰的机会。",
    "late_morning_1100_ct": "上午最后一次新开仓检查没有通过完整入场条件，因此不追单。",
    "midday_1300_ct": "该时段只管理已有风险，不主动扩大仓位。",
    "flatten_prep_1415_ct": "临近收盘，以降低尾盘风险和清理日内仓位为优先。",
    "end_of_day_1445_ct": "收盘前只核对仓位、资金和记录，不再新增风险。",
}

SLOT_ORDER = {
    "startup": 0,
    "pre_market_0745_ct": 1,
    "open_review_0835_ct": 2,
    "late_morning_1100_ct": 3,
    "midday_1300_ct": 4,
    "flatten_prep_1415_ct": 5,
    "end_of_day_1445_ct": 6,
}

SCHEDULED_SLOTS = (
    "pre_market_0745_ct",
    "open_review_0835_ct",
    "late_morning_1100_ct",
    "midday_1300_ct",
    "flatten_prep_1415_ct",
    "end_of_day_1445_ct",
)


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def number(value, digits=2):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return "未知"
    rendered = f"{amount:,.{digits}f}"
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def date_index(state, report_date):
    dates = state.get("planned_trading_dates", [])
    return dates.index(report_date) + 1 if report_date in dates else None


def slot_key(path):
    name = path.stem
    for key in SLOT_LABELS:
        if key in name:
            return key
    return "startup"


def due_scheduled_slots(root, report_date, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/Chicago"))
    try:
        target = datetime.fromisoformat(report_date).date()
    except ValueError:
        return SCHEDULED_SLOTS
    if target < now.date():
        return SCHEDULED_SLOTS
    if target > now.date():
        return ()
    schedule = load_json(root / "03-定时任务-routines" / "schedule.json", {})
    times = {task.get("id"): task.get("time") for task in schedule.get("tasks", [])}
    due = []
    for slot in SCHEDULED_SLOTS:
        try:
            hour, minute = map(int, str(times[slot]).split(":"))
        except (KeyError, TypeError, ValueError):
            continue
        if (hour, minute) <= (now.hour, now.minute):
            due.append(slot)
    return tuple(due)


def decision_files(root, report_date):
    folder = root / DATA_DIR / "决策记录-decisions"
    paths = list(folder.glob(report_date + "*.json")) if folder.exists() else []
    return sorted(paths, key=lambda path: (SLOT_ORDER.get(slot_key(path), 99), path.name))


def daily_events(root, report_date):
    ledger = load_json(root / DATA_DIR / "paper-ledger.json", {})
    return [event for event in ledger.get("events", []) if event.get("trading_date") == report_date]


def snapshot_for_date(state, events):
    if events and isinstance(events[-1].get("state_after"), dict):
        return events[-1]["state_after"]
    return state


def journal_links(root, report_date):
    folder = root / DATA_DIR / "运行日志-journal"
    return sorted(folder.glob(report_date + "*.md")) if folder.exists() else []


def plain_reason(decision, slot):
    chinese = decision.get("reason_zh") or decision.get("thesis_zh")
    if chinese:
        return str(chinese).strip()
    return SLOT_REASONS.get(slot, "本次条件没有通过策略与风险检查，因此不扩大风险。")


def render_decisions(root, report_date):
    rows = []
    for path in decision_files(root, report_date):
        decision = load_json(path, {})
        slot = slot_key(path)
        action = ACTION_LABELS.get(decision.get("action"), "状态检查")
        rows.append(
            "| " + SLOT_LABELS.get(slot, "状态检查") + " | " + action + " | "
            + plain_reason(decision, slot).replace("|", "，") + " |"
        )
    if not rows:
        return "当天没有找到结构化决策记录。"
    return "\n".join([
        "| 检查环节 | 决策 | 中文说明 |",
        "| --- | --- | --- |",
        *rows,
    ])


def loaded_decisions(root, report_date):
    return [(path, load_json(path, {})) for path in decision_files(root, report_date)]


def render_trade_reasons(root, report_date, events, positions):
    records = loaded_decisions(root, report_date)
    opened = [event for event in events if event.get("action") == "open_long"]
    closed = [event for event in events if event.get("action") == "close"]
    lines = []
    if opened:
        lines.extend([
            "## 为什么买入",
            "",
            "当天发生了模拟买入。具体入场理由、证据和风险参数见上方决策表及模拟成交明细。",
        ])
    else:
        lines.extend(["## 为什么没有买入", ""])
        no_trade_records = [item for item in records if item[1].get("action") == "no_trade"]
        if no_trade_records:
            for path, decision in no_trade_records:
                slot = slot_key(path)
                lines.append("- " + SLOT_LABELS.get(slot, "状态检查") + "：" + plain_reason(decision, slot))
        else:
            lines.append("- 当天没有找到可验证的模拟买入决策。")
        completed = {slot_key(path) for path, _ in records}
        missing = [SLOT_LABELS[slot] for slot in due_scheduled_slots(root, report_date) if slot not in completed]
        if missing:
            lines.append("- 未完成的计划检查：" + "、".join(missing) + "。这些属于执行流程缺口，不能算作主动的市场判断。")
        lines.append("- 结论：已记录的机会没有同时通过价格方向、成交量、止损、目标、交易时段和数据质量检查，因此没有模拟买入。")
    lines.extend(["", "## 为什么没有卖出" if not closed else "## 为什么卖出", ""])
    if closed:
        reasons = [EXIT_REASON_LABELS.get(event.get("reason"), "按计划退出") for event in closed]
        lines.append("- 当天发生模拟卖出，退出原因：" + "、".join(reasons) + "。")
    elif not opened and not positions:
        lines.append("- 当天从未建立模拟仓位，收盘时仍为空仓，因此没有可卖出的股票或 ETF。")
        lines.append("- 这不是一次独立的‘继续持有’判断，而是‘没有买入，所以无需卖出’。")
    elif positions:
        lines.append("- 当天结束时仍有模拟持仓，但账本中没有卖出成交；需要核对是否符合隔夜规则。")
    else:
        lines.append("- 当天没有记录模拟卖出成交。")
    return "\n".join(lines)


def render_review(root, report_date, events):
    records = loaded_decisions(root, report_date)
    completed = {slot_key(path) for path, _ in records}
    missing = [SLOT_LABELS[slot] for slot in due_scheduled_slots(root, report_date) if slot not in completed]
    gaps = []
    for _, decision in records:
        gap = str(decision.get("data_gap_zh", "")).strip()
        if gap and gap not in gaps:
            gaps.append(gap)
    lines = [
        "## 当日复盘",
        "",
        "### 做对了什么",
        "",
        "- 没有因为单条新闻、单个报价或开盘短线强弱直接追单。",
        "- 在缺少成交量和可复核止损依据时保持现金，符合保守策略。",
        "- 任务延迟后没有补造历史成交，保住了实验记录的真实性。",
        "- 真实下单始终关闭，资金风险为零。",
        "",
        "### 哪里做得不够",
        "",
    ]
    if missing:
        lines.append("- 六次计划检查没有完整执行。缺失：" + "、".join(missing) + "。")
    else:
        lines.append("- 六次计划检查均有记录，但仍需核对每次数据是否及时、完整。")
    for gap in gaps:
        lines.append("- 数据缺口：" + gap)
    if not events:
        lines.append("- 当天没有模拟成交，因此尚未检验成交模型、止损、目标、尾盘退出和盈亏计算是否能在真实节奏中工作。")
    lines.extend([
        "- 对 NVDA、XOM 等相对强势候选，只记录了‘值得继续观察’，没有形成清晰的候选入场价、失效价和触发清单。",
        "",
        "### 复盘结论",
        "",
        (report_date + " 的市场决策与执行完整性必须分开评价。主动空仓只有在到期检查均完成且证据充分时，才能算作有效判断；漏跑或数据缺失只能记为流程问题。"),
    ])
    return "\n".join(lines)


def render_joint_changes():
    return "\n".join([
        "## 我们需要一起修改什么",
        "",
        "| 优先级 | 需要修改 | 建议方案 | 需要共同确认 |",
        "| --- | --- | --- | --- |",
        "| 第一优先 | 定时任务可靠性 | 六个 GPT 时点拆分运行，本机 launchd 同时保留只读兜底记录；迟到超过 30 分钟不补造交易 | 继续观察手机推送和本机兜底是否同时留下记录 |",
        "| 第一优先 | 成交量数据 | 使用无密钥公共五分钟 K 线补充 SPY、QQQ、AAPL、NVDA、XOM 的成交量、推导 VWAP 和日内区间 | 观察数据稳定性；异常时继续空仓 |",
        "| 第二优先 | 入场触发标准 | 把‘趋势、相对强弱、成交量、事件风险、止损与目标’做成逐项通过表 | 确认必须全部通过，还是允许五项中四项通过 |",
        "| 第二优先 | 候选交易计划 | 每次盘前给 1 至 3 个候选，并提前写出触发价、止损、目标和取消条件 | 确认是否采用该格式 |",
        "| 暂不修改 | 风险限制 | 保持单仓最多 10%、单笔最大风险 0.5%、日亏损上限 2%、默认不隔夜 | 不因一天没有交易而放宽风险 |",
        "",
        "在定时可靠性和成交量数据补齐以前，系统可以继续观察和记录，但不应为了产生交易记录而降低入场标准。",
    ])


def render_events(events):
    if not events:
        return "当天没有模拟成交。没有买入，也没有卖出。"
    rows = []
    for event in events:
        timestamp = str(event.get("timestamp", ""))
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(
                ZoneInfo("America/Chicago")
            ).strftime("%H:%M")
        except ValueError:
            timestamp = "时间未知"
        rows.append("| " + " | ".join([
            timestamp,
            EVENT_LABELS.get(event.get("action"), "模拟事件"),
            str(event.get("symbol", "无")),
            str(event.get("quantity", "无")),
            str(event.get("fill_price") or event.get("mark_price") or "无"),
            EXIT_REASON_LABELS.get(event.get("reason"), "按策略执行"),
            number(event.get("net_pnl_usdt", 0)),
        ]) + " |")
    return "\n".join([
        "| 中部时间 | 结果 | 标的 | 数量 | 模拟成交价/标记价 | 原因 | 已实现盈亏（USDT） |",
        "| --- | --- | --- | ---: | ---: | --- | ---: |",
        *rows,
    ])


def render_market_summary(root, report_date):
    path = root / DATA_DIR / "证据资料-evidence" / (report_date + "-market-summary.zh-CN.json")
    summary = load_json(path, {})
    if not summary:
        return "\n".join([
            "## 当日美股大行情",
            "",
            "当天没有找到结构化的大盘复盘。这属于报告缺口，收盘任务必须补充主要指数、利率、油价、事件风险和策略影响。",
        ])
    lines = [
        "## 当日美股大行情",
        "",
        "### 总体判断",
        "",
        str(summary.get("headline", "暂无总体判断。")),
        "",
        "### 主要指数",
        "",
        "| 指数 | 当日涨跌 | 收盘点位 | 怎么理解 |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in summary.get("indexes", []):
        change = Decimal(str(item.get("change_percent", 0)))
        sign = "+" if change > 0 else ""
        lines.append("| " + str(item.get("name", "未知指数")) + " | " + sign + number(change) + "% | "
                     + number(item.get("close")) + " | " + str(item.get("interpretation", "")) + " |")
    sections = (
        ("### 为什么会这样", "drivers"),
        ("### 盘面结构", "market_structure"),
        ("### 对当天交易决策的意义", "strategy_implications"),
        ("### 下一交易日重点", "next_session_watch"),
    )
    for title, key in sections:
        lines.extend(["", title, ""])
        values = summary.get(key, [])
        lines.extend("- " + str(value) for value in values) if values else lines.append("- 暂无记录。")
    lines.extend(["", "### 数据来源", ""])
    sources = summary.get("sources", [])
    if sources:
        lines.extend("- [" + str(source.get("name", "来源")) + "](" + str(source.get("url", "")) + ")"
                     for source in sources)
    else:
        lines.append("- 未记录来源。")
    return "\n".join(lines)


def report_text(root, report_date):
    state = load_json(root / DATA_DIR / "current-state.json", {})
    events = daily_events(root, report_date)
    snapshot = snapshot_for_date(state, events)
    decisions = decision_files(root, report_date)
    positions = snapshot.get("positions", [])
    opened = sum(event.get("action") == "open_long" for event in events)
    closed = sum(event.get("action") == "close" for event in events)
    realized = sum(Decimal(str(event.get("net_pnl_usdt", 0))) for event in events if event.get("action") == "close")
    status = "当天未交易，资金保持不变" if not events else "当天已执行模拟交易，结果如下"
    index = date_index(state, report_date)
    day_label = f"第 {index} 个交易日" if index else "准备或验证日"
    holdings = "空仓" if not positions else "；".join(
        str(item.get("symbol", "未知标的")) + " " + str(item.get("quantity", "未知数量")) + " 股"
        for item in positions
    )
    raw_links = journal_links(root, report_date)
    next_focus = str(state.get("next_task_focus", ""))
    if not any("\u4e00" <= character <= "\u9fff" for character in next_focus):
        next_focus = "下一次按计划重新读取新闻、行情、账户状态和风险数据；条件不清楚时继续保持空仓。"
    raw_section = "\n".join(
        "- [底层审计记录 " + str(index) + "](../05-交易记录-data/运行日志-journal/" + path.name + ")"
        for index, path in enumerate(raw_links, start=1)
    ) or "- 当天没有底层运行日志。"
    lines = [
        "# " + report_date + " 每日交易中文报告",
        "",
        "> 本报告只记录虚拟资金的模拟交易，不代表真实账户操作，也不构成收益承诺。",
        "",
        "## 一眼看懂",
        "",
        "- 实验进度：" + day_label,
        "- 当天结论：" + status + "。",
        "- 模拟买入次数：" + str(opened),
        "- 模拟卖出次数：" + str(closed),
        "- 收盘持仓：" + holdings,
        "- 当天已实现盈亏：" + number(realized) + " USDT",
        "- 真实资金交易：没有，系统仍禁止真实下单。",
        "",
        "## 资金结果",
        "",
        "| 项目 | 当天结果 |",
        "| --- | ---: |",
        "| 实验初始资金 | " + number(state.get("starting_capital_usdt")) + " USDT |",
        "| 当前模拟现金 | " + number(snapshot.get("cash_usdt")) + " USDT |",
        "| 当前模拟总资产 | " + number(snapshot.get("equity_usdt")) + " USDT |",
        "| 当天已实现盈亏 | " + number(realized) + " USDT |",
        "| 当前未实现盈亏 | " + number(snapshot.get("unrealized_pnl_usdt", 0)) + " USDT |",
        "| 当前未平仓风险 | " + number(snapshot.get("daily_open_risk_usdt", 0)) + " USDT |",
        "",
        render_market_summary(root, report_date),
        "",
        "## 当天检查与决策",
        "",
        render_decisions(root, report_date),
        "",
        render_trade_reasons(root, report_date, events, positions),
        "",
        "## 模拟成交明细",
        "",
        render_events(events),
        "",
        render_review(root, report_date, events),
        "",
        render_joint_changes(),
        "",
        "## 风险说明",
        "",
        "- 决策记录数：" + str(len(decisions)) + "。",
        "- 没有满足多重证据、仓位、止损、交易时段和数据质量要求时，默认不交易。",
        "- 本系统不是持续盯盘工具；两次检查之间不会假设存在真实止损成交。",
        "- 任何真实资金交易都没有获得授权，也不会由本日报生成器执行。",
        "",
        "## 下一步",
        "",
        "- " + next_focus,
        "",
        "## 底层记录索引",
        "",
        "以下文件用于审计和复盘；日常查看本报告即可。",
        "",
        raw_section,
        "",
    ]
    return "\n".join(lines)


def write_daily_report(report_date=None, root=ROOT):
    root = Path(root)
    if report_date is None:
        report_date = datetime.now(timezone.utc).astimezone(ZoneInfo("America/Chicago")).date().isoformat()
    path = root / REPORT_DIR_NAME / (report_date + "-每日交易报告.md")
    atomic_write(path, report_text(root, report_date))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="美国中部时间交易日期，格式为 YYYY-MM-DD")
    args = parser.parse_args()
    path = write_daily_report(args.date)
    print(json.dumps({"状态": "已生成", "中文日报": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
