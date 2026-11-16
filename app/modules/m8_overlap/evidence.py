import csv
import io


def bill_csv(data):
    """正式账单的可复核证据：渠道账单、重叠组裁决、版本链三段。"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    bill = data["overlap_bill"]
    manifest = data["manifest"]
    writer.writerow(["账单号", manifest["bill_id"], "版本", f"V{manifest['version']}",
                     "规则版本", manifest["rule_version"], "生成时间", manifest["created_at"]])
    writer.writerow(["裁决依据", bill["rule_basis"]])
    writer.writerow([])
    writer.writerow(["# 渠道应付账单"])
    writer.writerow(["渠道", "账日(北京时间)", "有效曝光", "冲销", "重叠曝光",
                     "保留曝光", "原始费用", "冲销抵扣", "重叠抵扣", "应付", "状态", "判断依据"])
    for row in bill["channel_bills"]:
        writer.writerow([
            row["channel"], row["day"], row["impressions"], row["reversed"],
            row["overlap_losers"], row["retained"], row["gross"],
            row["reversal_credit"], row["overlap_credit"], row["net"],
            row["status"], row["basis"],
        ])
    summary = bill["summary"]
    writer.writerow(["合计", "", "", "", summary["overlap_impressions"], "",
                     summary["gross"], summary["reversal_credit"],
                     summary["overlap_credit"], summary["net"],
                     "金额守恒" if summary["amount_ok"] else "守恒失败",
                     "一次抵扣" if summary["deduction_once_ok"] else "重复抵扣风险"])
    writer.writerow([])
    writer.writerow(["# 跨渠道重叠组（收入保留与抵扣依据）"])
    for group in bill["overlap_groups"]:
        winner = group["winner"]
        writer.writerow(["重叠组", group["group_id"], "活动", group["campaign_id"],
                         "用户", group["user_id"], "窗口起", group["window_start_bj"],
                         "窗口止", group["window_end_bj"]])
        writer.writerow(["保留", winner["event_id"], winner["channel"], winner["at_bj"],
                         "来源行", winner["line"], "保留收入(未舍入)", winner["retained_revenue_raw"],
                         winner["basis"]])
        for loser in group["losers"]:
            writer.writerow(["抵扣", loser["event_id"], loser["channel"], loser["at_bj"],
                             "来源行", loser["line"], "抵扣额(未舍入)", loser["amount_raw"],
                             "间隔(分钟)", loser["gap_minutes"], loser["basis"]])
    writer.writerow([])
    writer.writerow(["# 版本链"])
    writer.writerow(["账单号", "基础账单", "父版本", "版本", "类型", "来源摘要", "生成时间"])
    for item in data.get("history", []):
        writer.writerow([item["bill_id"], item["base_id"], item["parent_id"] or "",
                         f"V{item['version']}", item["kind"], item["source_digest"], item["created_at"]])
    return "﻿" + buffer.getvalue()
