from decimal import Decimal
from app.modules.m4_calculate.service import run
from app.modules.m4_calculate.rules import settle
from app.modules.m3_model.service import run as model

def test_aggregate_before_round(clean): # TRAP-10
    a=run(clean)["results"][0]
    assert a["gross"]=="0.20" and a["net"]=="0.19"
    assert a["gross"]!=str((Decimal("12.5")/1000).quantize(Decimal("0.01"))*16)
def test_reversal_cap(dirty):assert [x["code"] for x in run(dirty)["quarantine"]].count("OVER_REVERSE")==1
def test_net_b(dirty):assert run(dirty)["results"][1]["net"]=="0.34"
def test_accepted(dirty):assert len(run(dirty)["rows"])==52
def test_same_origin_day(clean):assert run(clean)["results"][0]["day"]=="2026-11-01"
def test_invalid_reference(clean):
    rows=model(clean)["rows"];rows[-1]={**next(x for x in rows if x["kind"]=="reversal"),"ref":"missing"};_,_,bad=settle(rows)
    assert bad[0]["code"]=="REFERENCE"
def test_channel_rejected(clean):
    rows=model(clean)["rows"];rows=[{**x,"channel":"DSP-B"} if x["kind"]=="reversal" else x for x in rows];_,_,bad=settle(rows)
    assert bad[0]["code"]=="CHANNEL"
