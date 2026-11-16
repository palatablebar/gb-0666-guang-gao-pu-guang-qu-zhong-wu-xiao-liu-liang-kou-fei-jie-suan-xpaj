import json
import time

from app.config import RULE_VERSION
from app.errors import reject
from app.modules.m1_intake.service import source
from app.modules.m6_reconcile.service import run as pipeline
from app.store import save_bill_version, fetch_bill, bill_history
from .manifest import digest_of, bill_manifest
from .rules import build_bill, merge_backfill, event_key_set


def _settle(options):
    """复用 M1→M6 全量管线后追加跨渠道裁决，纯计算不写 runs 表。"""
    result = pipeline(options)
    result["overlap_bill"] = build_bill(result["rows"])
    return result


def _hydrate(row):
    data = json.loads(row["body"])
    data["manifest"]["version"] = row["version"]
    data["manifest"]["kind"] = row["kind"]
    data["manifest"]["parent_id"] = row["parent_id"]
    data["manifest"]["base_id"] = row["base_id"]
    data["revision"] = row["version"]
    data["decision"] = "待复核"
    return data


def _archive(bill_id, parent_id, source_text, kind, result, base_id=None):
    source_digest = digest_of(source_text)
    digest = digest_of({"source": source_digest, "rule": RULE_VERSION})
    start = time.perf_counter()
    manifest = bill_manifest(
        digest, bill_id, version=1, elapsed=0,
        kind=kind, parent_id=parent_id, base_id=base_id,
    )
    result["manifest"] = manifest
    row, created = save_bill_version(
        bill_id=bill_id, parent_id=parent_id, digest=digest,
        source_digest=source_digest, source_text=source_text,
        kind=kind, body=result, base_id=base_id,
    )
    manifest["elapsed_ms"] = round((time.perf_counter() - start) * 1000)
    stored = _hydrate(row)
    # 幂等重试命中既有版本时，以本次输入重算补数元数据，避免返回旧批次的计数
    if not created and kind == "backfill":
        stored["backfill"] = result["backfill"]
    stored["created"] = created
    stored["history"] = bill_history(bill_id)
    return stored


def run(options=None):
    """首次结算：生成正式跨渠道账单并归档为 V1。"""
    options = options or {}
    if "backfill" in options or "base_bill_id" in options:
        reject("PARAMETER", "首次结算不接受补数参数")
    source_text = source(options).decode("utf-8")
    result = _settle(options)
    bill_id = digest_of(source_text)[:16]
    return _archive(bill_id, None, source_text, "initial", result)


def backfill(base_bill_id, backfill_text):
    """晚到曝光补齐后再次结算。

    先取旧版账单与原台账，校验/合并全部成功后才计算并写入新版本；
    任一步失败都抛 DomainError，旧版账单原样保留。
    """
    if not isinstance(backfill_text, str) or not backfill_text.strip():
        reject("BACKFILL_SCHEMA", "补数内容须为非空CSV文本，旧版账单保留")
    base_row = fetch_bill(base_bill_id)
    merged_text, _ = merge_backfill(base_row["source_text"], backfill_text)
    # 以旧版台账为基准用语义事件集合判断：同批重试不引入任何新曝光或抵扣
    new_keys = event_key_set(merged_text) - event_key_set(base_row["source_text"])
    added = len(new_keys)
    idempotent = added == 0
    result = _settle({"text": merged_text})
    result["backfill"] = {
        "base_bill_id": base_bill_id,
        "base_version": base_row["version"],
        "added_events": added,
        "retry_idempotent": idempotent,
    }
    return _archive(
        bill_id=base_row["bill_id"], parent_id=base_row["bill_id"],
        source_text=merged_text, kind="backfill", result=result,
        base_id=base_row["base_id"],
    )


def load(bill_id, version=None):
    row = fetch_bill(bill_id, version)
    data = _hydrate(row)
    data["history"] = bill_history(bill_id)
    return data
