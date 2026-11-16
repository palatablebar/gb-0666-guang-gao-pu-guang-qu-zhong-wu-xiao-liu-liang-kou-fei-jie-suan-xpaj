import pytest
from app.modules.m5_quarantine.service import run
from app.modules.m5_quarantine.rules import distribution,select,evidence
from app.errors import DomainError

def test_distribution(dirty):assert run(dirty)["reason_counts"]=={"DUPLICATE":1,"MISSING":1,"OVER_REVERSE":1,"TIME":1}
def test_clean(clean):assert run(clean)["reason_counts"]=={}
def test_complete(dirty):assert run(dirty)["evidence_complete"] is True
def test_select(dirty):assert len(select(run(dirty)["quarantine"],"OVER_REVERSE"))==1
def test_evidence_row(dirty):assert all(x["line"]>=2 for x in run(dirty)["quarantine"])
def test_unknown(dirty):
    with pytest.raises(DomainError):select(run(dirty)["quarantine"],"WRONG")
def test_incomplete():assert evidence([{"line":1,"code":"VALUE"}]) is False
