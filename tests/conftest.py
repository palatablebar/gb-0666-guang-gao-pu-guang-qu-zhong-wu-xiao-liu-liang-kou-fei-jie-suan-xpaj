import pytest
@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):monkeypatch.setenv("DATA_DIR",str(tmp_path))
@pytest.fixture
def dirty():return {"sample":"dirty"}
@pytest.fixture
def clean():return {"sample":"clean"}
