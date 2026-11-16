from decimal import Decimal
import pytest
from app.modules.m2_contract.service import run
from app.modules.m2_contract.rules import amount,contract,deduplicate
from app.errors import DomainError

def test_cpm(clean):assert run(clean)["rows"][0]["cpm"]=="12.50"
def test_big_id(clean): # TRAP-09
    assert run(clean)["rows"][0]["event_id"]=="9007199254740993000"
def test_fullwidth(): # TRAP-06
    assert amount("１，２３４．５０")==Decimal("1234.50")
def test_missing(dirty): # TRAP-07
    assert "MISSING" in [x["code"] for x in run(dirty)["quarantine"]]
def test_duplicate(dirty): # TRAP-14
    assert [x["code"] for x in run(dirty)["quarantine"]].count("DUPLICATE")==1
def test_utc(dirty): # TRAP-11
    assert run(dirty)["rows"][0]["at"]=="2026-10-31T18:01:00+00:00"
def test_invalid_currency():
    with pytest.raises(DomainError):contract({"frequency_cap":3,"channels":{"A":{"cpm":"1","currency":"USD"}}})
