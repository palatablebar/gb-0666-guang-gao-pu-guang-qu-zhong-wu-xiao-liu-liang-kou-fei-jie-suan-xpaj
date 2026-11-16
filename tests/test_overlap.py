import pytest
from fastapi.testclient import TestClient

from app.errors import DomainError
from app.main import app
from app.modules.m8_overlap.rules import adjudicate, build_bill, merge_backfill
from app.modules.m8_overlap.service import run, backfill, load
from app.store import bill_history, fetch_bill

HEADER = "event_id,at,channel,user_id,ip,kind,ref,bot,campaign_id\n"


def _bill(options):
    return run(options)["overlap_bill"]


def test_winner_keeps_revenue_losers_get_credit():
    bill = _bill({"sample": "overlap"})
    by_channel = {row["channel"]: row for row in bill["channel_bills"]}
    # DSP-B 在 U100/U400 两个重叠组中保留收入，仅对 U200 形成一次抵扣
    assert by_channel["DSP-B"]["overlap_losers"] == 3
    assert by_channel["DSP-C"]["overlap_losers"] == 2
    assert by_channel["DSP-A"]["overlap_losers"] == 0
    # 每组都有明确的保留方与抵扣方及书面判断依据
    for group in bill["overlap_groups"]:
        assert group["winner"]["basis"]
        for loser in group["losers"]:
            assert loser["code"] == "OVERLAP" and loser["basis"]


def test_window_boundary_inclusive_and_fixed_anchor():
    bill = _bill({"sample": "overlap"})
    # U200：10:03(A) 锚点；10:33(B) 恰好 30 分钟计入窗口；10:40(C) 超出另成窗口
    u200 = next(g for g in bill["overlap_groups"] if g["user_id"] == "U200")
    assert u200["winner"]["event_id"] == "OV-1004"
    assert [x["event_id"] for x in u200["losers"]] == ["OV-1005"]


def test_reversed_and_bot_excluded_from_overlap():
    bill = _bill({"sample": "overlap"})
    ids = {x["event_id"] for g in bill["overlap_groups"] for x in g["losers"]}
    # OV-1001 已被合法冲销，不参与重叠裁决；OV-2004 为机器流量，不进入有效曝光
    assert "OV-1001" not in ids
    assert "OV-2004" not in {g["winner"]["event_id"] for g in bill["overlap_groups"]}


def test_money_conservation_and_single_deduction():
    bill = _bill({"sample": "overlap"})
    s = bill["summary"]
    assert s["amount_ok"] is True
    assert s["deduction_once_ok"] is True
    assert s["gross"] == "0.17"
    assert s["overlap_credit"] == "0.07"
    assert s["net"] == "0.09"


def test_same_channel_repeat_is_not_overlap():
    text = HEADER + (
        "E1,2026-11-01T09:00:00+08:00,DSP-A,U1,1.1.1.1,impression,,0,C1\n"
        "E2,2026-11-01T09:10:00+08:00,DSP-A,U1,1.1.1.1,impression,,0,C1\n"
        "E3,2026-11-01T09:20:00+08:00,DSP-B,U1,1.1.1.2,impression,,0,C1\n"
    )
    bill = _bill({"text": text})
    group = bill["overlap_groups"][0]
    # 同渠道第二条不抵扣，仅跨渠道的 E3 被抵扣
    assert [x["event_id"] for x in group["losers"]] == ["E3"]
    dsp_a = next(x for x in bill["channel_bills"] if x["channel"] == "DSP-A")
    assert dsp_a["overlap_losers"] == 0 and dsp_a["retained"] == 2


def test_judge_is_order_invariant():
    rows = run({"sample": "overlap"})
    # 直接对裁决函数做乱序输入，结果结构应一致
    base = adjudicate(rows["rows"])
    shuffled = adjudicate(list(reversed(rows["rows"])))
    assert [(g["group_id"], g["winner"]["event_id"]) for g in base[0]] == \
           [(g["group_id"], g["winner"]["event_id"]) for g in shuffled[0]]


def test_backfill_creates_new_version_keeps_old():
    v1 = run({"sample": "overlap"})
    bid = v1["manifest"]["bill_id"]
    backfill_text = (
        HEADER + "OV-1000,2026-11-01T09:55:00+08:00,DSP-B,U100,192.0.2.30,impression,,0,CMP-100\n"
    )
    v2 = backfill(bid, backfill_text)
    assert v2["manifest"]["version"] == 2 and v2["created"] is True
    assert v2["backfill"]["added_events"] == 1 and v2["backfill"]["retry_idempotent"] is False
    # 晚到曝光成为新锚点，收入保留方由 DSP-A 侧的 OV-1002 变为更早的 DSP-B OV-1000
    u100 = next(g for g in v2["overlap_bill"]["overlap_groups"] if g["user_id"] == "U100")
    assert u100["winner"]["event_id"] == "OV-1000"
    # 旧版 V1 原样保留可复核
    old = load(bid, 1)
    old_u100 = next(g for g in old["overlap_bill"]["overlap_groups"] if g["user_id"] == "U100")
    assert old_u100["winner"]["event_id"] == "OV-1002"
    assert old["overlap_bill"]["summary"]["net"] == "0.09"
    assert [(h["version"], h["kind"]) for h in bill_history(bid)] == [
        (1, "initial"), (2, "backfill")
    ]


def test_identical_retry_is_idempotent_no_new_version():
    v1 = run({"sample": "overlap"})
    bid = v1["manifest"]["bill_id"]
    backfill_text = (
        HEADER + "OV-1000,2026-11-01T09:55:00+08:00,DSP-B,U100,192.0.2.30,impression,,0,CMP-100\n"
    )
    first = backfill(bid, backfill_text)
    retry = backfill(bid, backfill_text)
    assert first["created"] is True
    assert retry["created"] is False
    assert retry["manifest"]["version"] == 2
    assert retry["backfill"]["added_events"] == 0
    assert retry["backfill"]["retry_idempotent"] is True
    assert len(bill_history(bid)) == 2


def test_backfill_failure_preserves_old_bill():
    v1 = run({"sample": "overlap"})
    bid = v1["manifest"]["bill_id"]
    # 结构错误
    with pytest.raises(DomainError) as exc:
        backfill(bid, "bad,header\n1,2")
    assert exc.value.code == "BACKFILL_SCHEMA"
    # 同 ID 字段冲突
    with pytest.raises(DomainError) as exc:
        backfill(bid, HEADER + "OV-1001,2026-11-01T10:00:00+08:00,DSP-A,U100,9.9.9.9,impression,,0,CMP-100\n")
    assert exc.value.code == "BACKFILL_CONFLICT"
    # 基础账单不存在
    with pytest.raises(DomainError) as exc:
        backfill("0000000000000000", HEADER + "X,2026-11-01T10:00:00+08:00,DSP-A,U1,1.1.1.1,impression,,0,C1\n")
    assert exc.value.code == "NOT_FOUND"
    # 失败后仍只有 V1，金额未变
    latest = load(bid)
    assert latest["manifest"]["version"] == 1
    assert latest["overlap_bill"]["summary"]["net"] == "0.09"


def test_backfill_never_double_counts_known_events():
    v1 = run({"sample": "overlap"})
    bid = v1["manifest"]["bill_id"]
    known = (
        HEADER + "OV-1001,2026-11-01T10:00:00+08:00,DSP-A,U100,192.0.2.10,impression,,0,CMP-100\n"
    )
    result = backfill(bid, known)
    assert result["created"] is False
    assert result["backfill"]["added_events"] == 0
    # 有效曝光数与 V1 完全一致，未新增曝光或抵扣
    assert result["overlap_bill"]["summary"] == v1["overlap_bill"]["summary"]


def test_merge_backfill_detects_schema_and_conflict():
    base = HEADER + "E1,2026-11-01T09:00:00+08:00,DSP-A,U1,1.1.1.1,impression,,0,C1\n"
    with pytest.raises(DomainError) as exc:
        merge_backfill(base, "wrong,cols\n1,2")
    assert exc.value.code == "BACKFILL_SCHEMA"
    with pytest.raises(DomainError) as exc:
        merge_backfill(base, HEADER + "E1,2026-11-01T09:00:00+08:00,DSP-A,U1,8.8.8.8,impression,,0,C1\n")
    assert exc.value.code == "BACKFILL_CONFLICT"


def test_http_endpoints_and_evidence():
    with TestClient(app) as client:
        created = client.get("/api/overlap?sample=overlap")
        assert created.status_code == 200
        bid = created.json()["manifest"]["bill_id"]
        backfill_text = (
            HEADER + "OV-1000,2026-11-01T09:55:00+08:00,DSP-B,U100,192.0.2.30,impression,,0,CMP-100\n"
        )
        resp = client.post(f"/api/overlap/bills/{bid}/backfill", json={"text": backfill_text})
        assert resp.status_code == 200 and resp.json()["manifest"]["version"] == 2
        bad = client.post(f"/api/overlap/bills/{bid}/backfill", json={"text": "bad,header\n1,2"})
        assert bad.status_code == 422 and bad.json()["detail"]["code"] == "BACKFILL_SCHEMA"
        evidence = client.get(f"/api/overlap/bills/{bid}/evidence.csv")
        assert evidence.status_code == 200
        text = evidence.text
        assert "渠道应付账单" in text and "OVERLAP" not in text  # 证据用中文结论，不暴露裸码
        assert "版本链" in text and "backfill" in text
        page = client.get(f"/overlap?run_id={bid}")
        assert page.status_code == 200 and "渠道应付正式账单" in page.text


def test_legacy_eight_column_csv_defaults_campaign():
    text = "event_id,at,channel,user_id,ip,kind,ref,bot\n" \
           "L1,2026-11-01T09:00:00+08:00,DSP-A,U1,1.1.1.1,impression,,0\n" \
           "L2,2026-11-01T09:05:00+08:00,DSP-B,U1,1.1.1.2,impression,,0\n"
    bill = _bill({"text": text})
    assert bill["overlap_groups"][0]["campaign_id"] == "CMP-DEFAULT"
    assert bill["overlap_groups"][0]["winner"]["event_id"] == "L1"
