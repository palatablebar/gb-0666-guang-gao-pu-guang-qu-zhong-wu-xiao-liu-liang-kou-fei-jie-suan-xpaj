import pytest
from app.modules.m7_batches.service import run
from app.modules.m7_batches.rules import csv_evidence
from app.store import review,fetch,history
from app.errors import DomainError

def test_idempotent(dirty):a=run(dirty);b=run(dirty);assert a["manifest"]["run_id"]==b["manifest"]["run_id"];assert len(history())==1
def test_input_change(dirty,clean):assert run(dirty)["manifest"]["run_id"]!=run(clean)["manifest"]["run_id"]
def test_review(clean):a=run(clean);assert review(a["manifest"]["run_id"],1,"通过")["revision"]==2
def test_stale(dirty): # TRAP-26
    a=run(dirty);rid=a["manifest"]["run_id"];review(rid,1,"通过")
    with pytest.raises(DomainError):review(rid,1,"退回")
def test_export_invalid(dirty):assert "BOT" in csv_evidence(run(dirty))
def test_saved(dirty):a=run(dirty);assert fetch(a["manifest"]["run_id"])["reconciliation"]["net"]=="0.69"
def test_invalid_parameter():
    with pytest.raises(DomainError):run({"params":{"unknown":1}})

def test_review_rejects_structured_parameters(dirty):
    a=run(dirty);rid=a["manifest"]["run_id"]
    with pytest.raises(DomainError):review(rid,[],"通过")
    with pytest.raises(DomainError):review(rid,1,[])
