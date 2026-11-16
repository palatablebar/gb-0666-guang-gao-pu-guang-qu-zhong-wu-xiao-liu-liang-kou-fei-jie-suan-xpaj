import pytest
from app.modules.m1_intake.service import run
from app.modules.m1_intake.rules import read
from app.errors import DomainError

def test_dirty_count(dirty):assert run(dirty)["input_count"]==59
def test_clean_count(clean):assert len(run(clean)["rows"])==49
def test_bom(dirty): # TRAP-02
    assert run(dirty)["rows"][0]["event_id"]=="9007199254740993000"
def test_gb18030(): # TRAP-01
    assert run({"sample":"gb18030"})["encoding"]=="gb18030"
def test_raw_id(dirty):assert isinstance(run(dirty)["rows"][0]["event_id"],str)
def test_empty():
    with pytest.raises(DomainError,match="文件为空"):read(b"")
def test_unknown():
    with pytest.raises(DomainError):run({"sample":"wrong"})
