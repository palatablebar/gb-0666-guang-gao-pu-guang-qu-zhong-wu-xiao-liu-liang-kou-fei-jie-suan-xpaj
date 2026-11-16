"""跨渠道重叠曝光裁决与正式账单生成。

规则：同一活动(campaign_id)对同一用户(user_id)的曝光，以窗口内最早一条为锚点，
锚点之后 30 分钟（含边界）内的曝光构成同一触达窗口；窗口内跨渠道的重复触达，
广告主只为一次有效触达付费——最早曝光渠道保留收入，其余渠道按各自合同 CPM
形成重叠抵扣。同一渠道的后续曝光仍按频次合同计费，不参与重叠抵扣。
已被合法冲销的曝光不再参与重叠裁决，避免同一曝光重复抵扣。
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import csv
import io

from app.config import OVERLAP_WINDOW_MINUTES
from app.errors import reject
from app.modules.m1_intake.rules import read as intake_read

BEIJING = timezone(timedelta(hours=8))
CENT = Decimal("0.01")


def _row_fingerprint(row):
    return {key: value for key, value in row.items() if key != "line"}


def merge_backfill(base_text, backfill_text):
    """把晚到曝光并入原始台账。

    成功才返回合并文本；任何结构性/冲突性错误都抛 DomainError，由调用方保证旧版账单不动。
    - 表头列数不一致：BACKFILL_SCHEMA
    - 补数 event_id 已存在且字段不同：BACKFILL_CONFLICT
    - 补数与原台账完全相同：幂等跳过，重试不新增曝光
    """
    try:
        base = intake_read(base_text.encode("utf-8"))
        extra = intake_read(backfill_text.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - 统一归为补数结构失败
        code = getattr(exc, "code", "BACKFILL_SCHEMA")
        reject("BACKFILL_SCHEMA", f"补数结构无效（{code}），旧版账单保留")
    if base["columns"] != extra["columns"]:
        reject("BACKFILL_SCHEMA", "补数表头与原账单台账不一致，旧版账单保留")
    fields = base["columns"]
    known = {row["event_id"]: _row_fingerprint(row) for row in base["rows"]}
    appended = []
    for row in extra["rows"]:
        fingerprint = _row_fingerprint(row)
        if row["event_id"] in known:
            if known[row["event_id"]] != fingerprint:
                reject("BACKFILL_CONFLICT",
                       f"补数曝光 {row['event_id']} 与原台账字段冲突，补数失败，旧版账单保留")
            continue  # 幂等：同批重试完全相同的记录直接跳过
        known[row["event_id"]] = fingerprint
        appended.append(fingerprint)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in base["rows"]:
        writer.writerow(_row_fingerprint(row))
    for row in appended:
        writer.writerow(row)
    return buffer.getvalue(), len(appended)


def event_key_set(text):
    """台账中的事件ID集合，用于判断补数是否引入原账单不存在的事件。"""
    return {row["event_id"] for row in intake_read(text.encode("utf-8"))["rows"]}


def _parse_at(value):
    return datetime.fromisoformat(value)


def _bj(value):
    return _parse_at(value).astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S")


def _event_value(row):
    return Decimal(row["cpm"]) / Decimal(1000)


def _round(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def reversed_originals(rows):
    """m4 已校验合法的冲销，返回被冲销原曝光ID集合。"""
    return {row["ref"] for row in rows if row["kind"] == "reversal"}


def build_clusters(impressions, window_minutes=OVERLAP_WINDOW_MINUTES):
    """按 (活动,用户) 分组，再以最早曝光为锚点切出 30 分钟触达窗口。

    锚点固定、窗口闭区间 [锚点, 锚点+30分钟]；窗口外的事件另起锚点。
    每个事件只落入一个窗口，因此一条曝光至多被抵扣一次。
    """
    grouped = defaultdict(list)
    for row in impressions:
        grouped[(row["campaign_id"], row["user_id"])].append(row)
    clusters = []
    for (campaign, user), items in grouped.items():
        items = sorted(items, key=lambda x: (_parse_at(x["at"]), x["channel"], x["event_id"]))
        anchor = None
        current = []
        for row in items:
            at = _parse_at(row["at"])
            if anchor is None or at > anchor + timedelta(minutes=window_minutes):
                if current:
                    clusters.append((campaign, user, current))
                current = [row]
                anchor = at
            else:
                current.append(row)
        if current:
            clusters.append((campaign, user, current))
    return sorted(clusters, key=lambda c: (c[0], c[1], _parse_at(c[2][0]["at"])))


def adjudicate(rows, window_minutes=OVERLAP_WINDOW_MINUTES):
    """返回 (重叠组明细, 抵扣曝光ID集合, 保留曝光ID集合)。"""
    reversed_ids = reversed_originals(rows)
    impressions = [
        row for row in rows
        if row["kind"] == "impression" and row["event_id"] not in reversed_ids
    ]
    groups = []
    loser_ids = set()
    winner_ids = set()
    for index, (campaign, user, cluster) in enumerate(build_clusters(impressions, window_minutes), start=1):
        winner = cluster[0]
        channels = {row["channel"] for row in cluster}
        if len(channels) == 1:
            continue
        winner_ids.add(winner["event_id"])
        losers = [row for row in cluster[1:] if row["channel"] != winner["channel"]]
        loser_ids.update(row["event_id"] for row in losers)
        window_anchor = _parse_at(cluster[0]["at"])
        window_end = window_anchor + timedelta(minutes=window_minutes)
        loser_items = []
        for row in losers:
            gap = (_parse_at(row["at"]) - window_anchor).total_seconds() / 60
            loser_items.append({
                "event_id": row["event_id"],
                "channel": row["channel"],
                "user_id": user,
                "at_bj": _bj(row["at"]),
                "line": row["line"],
                "amount_raw": str(_event_value(row)),
                "code": "OVERLAP",
                "gap_minutes": f"{gap:g}",
                "basis": (
                    f"与保留曝光 {winner['event_id']}（{winner['channel']} {_bj(winner['at'])}）"
                    f"同活动 {campaign} 同用户 {user}，间隔 {gap:g} 分钟≤{window_minutes}；"
                    f"一次有效触达已由 {winner['channel']} 计费，本渠道按自有 CPM {row['cpm']} 形成重叠抵扣"
                ),
            })
        groups.append({
            "group_id": f"OV-{index:04d}",
            "campaign_id": campaign,
            "user_id": user,
            "window_start_bj": window_anchor.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
            "window_end_bj": window_end.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
            "winner": {
                "event_id": winner["event_id"],
                "channel": winner["channel"],
                "at_bj": _bj(winner["at"]),
                "line": winner["line"],
                "retained_revenue_raw": str(_event_value(winner)),
                "basis": (
                    f"同活动 {campaign} 用户 {user} 在 {window_minutes} 分钟窗口内最早曝光，"
                    f"按先到先得由 {winner['channel']} 保留该次有效触达收入"
                ),
            },
            "losers": loser_items,
            "credit_raw": str(sum((Decimal(x["amount_raw"]) for x in loser_items), Decimal(0))),
        })
    return groups, loser_ids, winner_ids


def build_channel_bills(rows, groups, loser_ids):
    """按渠道+北京时间账日聚合正式账单，扣减分币守恒、尾差归入重叠抵扣。"""
    reversed_ids = reversed_originals(rows)
    buckets = {}

    def bucket(row):
        key = (row["channel"], row["day"])
        return buckets.setdefault(key, {
            "channel": row["channel"], "day": row["day"],
            "impressions": 0, "reversed": 0, "overlap_losers": 0,
            "gross_raw": Decimal(0), "reversal_raw": Decimal(0), "overlap_raw": Decimal(0),
            "lines": [],
        })

    for row in sorted((x for x in rows if x["kind"] == "impression"),
                      key=lambda x: (_parse_at(x["at"]), x["event_id"])):
        item = bucket(row)
        item["impressions"] += 1
        item["gross_raw"] += _event_value(row)
        item["lines"].append(row["line"])
        if row["event_id"] in reversed_ids:
            item["reversed"] += 1
            item["reversal_raw"] += _event_value(row)
        if row["event_id"] in loser_ids:
            item["overlap_losers"] += 1
            item["overlap_raw"] += _event_value(row)

    bills = []
    for key in sorted(buckets):
        item = buckets[key]
        gross = _round(item["gross_raw"])
        reversal_credit = _round(item["reversal_raw"])
        net = _round(item["gross_raw"] - item["reversal_raw"] - item["overlap_raw"])
        overlap_credit = gross - reversal_credit - net
        retained = item["impressions"] - item["reversed"] - item["overlap_losers"]
        status = "通过" if overlap_credit == 0 and reversal_credit == 0 else (
            "重叠抵扣" if overlap_credit > 0 and reversal_credit == 0 else "冲销+重叠抵扣"
            if reversal_credit > 0 and overlap_credit > 0 else "已扣减")
        bills.append({
            "channel": item["channel"],
            "day": item["day"],
            "impressions": item["impressions"],
            "reversed": item["reversed"],
            "overlap_losers": item["overlap_losers"],
            "retained": retained,
            "gross_raw": str(item["gross_raw"]),
            "reversal_raw": str(item["reversal_raw"]),
            "overlap_raw": str(item["overlap_raw"]),
            "gross": str(gross),
            "reversal_credit": str(reversal_credit),
            "overlap_credit": str(overlap_credit),
            "net": str(net),
            "status": status,
            "lines": item["lines"],
            "basis": "各渠道按自有CPM独立结账；最早曝光渠道保留收入，重叠渠道按分币守恒轧差抵扣",
        })
    return bills


def build_bill(rows, window_minutes=OVERLAP_WINDOW_MINUTES):
    groups, loser_ids, winner_ids = adjudicate(rows, window_minutes)
    channel_bills = build_channel_bills(rows, groups, loser_ids)
    gross = sum((Decimal(x["gross"]) for x in channel_bills), Decimal(0))
    reversal_credit = sum((Decimal(x["reversal_credit"]) for x in channel_bills), Decimal(0))
    overlap_credit = sum((Decimal(x["overlap_credit"]) for x in channel_bills), Decimal(0))
    net = sum((Decimal(x["net"]) for x in channel_bills), Decimal(0))
    overlap_impressions = sum(len(g["losers"]) for g in groups)
    amount_ok = gross - reversal_credit - overlap_credit == net
    once_ok = len(loser_ids) == overlap_impressions and (not loser_ids & winner_ids)
    return {
        "window_minutes": window_minutes,
        "currency": "CNY",
        "rule_basis": (
            f"同一活动对同一用户的曝光，以窗口内最早曝光为锚点，{window_minutes} 分钟（含边界）内"
            "跨渠道重复触达只计一次有效触达；最早曝光渠道保留重叠曝光收入，其余渠道按各自合同"
            "CPM 形成抵扣。已冲销曝光不参与重叠裁决，每条曝光至多抵扣一次。"
        ),
        "channel_bills": channel_bills,
        "overlap_groups": groups,
        "summary": {
            "overlap_groups": len(groups),
            "overlap_impressions": overlap_impressions,
            "retained_winners": len(winner_ids),
            "gross": str(gross),
            "reversal_credit": str(reversal_credit),
            "overlap_credit": str(overlap_credit),
            "net": str(net),
            "amount_ok": amount_ok,
            "deduction_once_ok": once_ok,
        },
    }
