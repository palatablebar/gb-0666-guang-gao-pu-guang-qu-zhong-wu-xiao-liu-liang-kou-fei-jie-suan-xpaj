from app.modules.m6_reconcile.service import run

def test_net_dirty(dirty):assert run(dirty)["reconciliation"]["net"]=="0.69"
def test_net_clean(clean):assert run(clean)["reconciliation"]["net"]=="0.64"
def test_count(dirty):assert run(dirty)["reconciliation"]["count_ok"] is True
def test_amount(dirty):assert run(dirty)["reconciliation"]["amount_ok"] is True
def test_duplicates(dirty):assert run(dirty)["reconciliation"]["duplicates"]==1
def test_quarantined(dirty):assert run(dirty)["reconciliation"]["quarantined"]==3
def test_channel_delta(dirty):assert run(dirty)["reconciliation"]["channels"][1]["difference"]=="-0.05"
