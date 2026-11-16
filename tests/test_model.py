from app.modules.m3_model.service import run
from app.modules.m3_model.rules import judge
from app.modules.m2_contract.service import run as contract

def test_bot(dirty):assert run(dirty)["invalid_counts"]["BOT"]==1
def test_cap(dirty):assert run(dirty)["invalid_counts"]["CAP"]==2
def test_clean(clean):assert run(clean)["invalid"]==[]
def test_accepted(dirty):assert len(run(dirty)["rows"])==53
def test_priority(dirty): # TRAP-19
    rows=contract(dirty)["rows"];a,invalid=judge(rows,1)
    assert next(x for x in invalid if x["event_id"]=="BOT-1")["code"]=="BOT"
def test_order_invariant(dirty):
    rows=contract(dirty)["rows"];assert judge(rows,3)==judge(list(reversed(rows)),3)
def test_reversal_not_cap(clean):assert next(x for x in run(clean)["rows"] if x["event_id"]=="R-1")["kind"]=="reversal"
