from fastapi.testclient import TestClient
from app.main import app
from app.config import MODULES

def test_pages_and_api():
    with TestClient(app) as c:
        for slug,_ in MODULES:
            assert c.get("/"+slug).status_code==200
            assert c.get("/api/"+slug).status_code==200
def test_export_and_no_loss_id():
    with TestClient(app) as c:
        data=c.post("/api/runs",json={"sample":"dirty"}).json()
        assert data["rows"][0]["event_id"]=="9007199254740993000"
        assert "BOT" in c.get('/api/runs/'+data["manifest"]["run_id"]+'/evidence.csv').text
def test_wrong_csv():
    with TestClient(app) as c:assert c.post("/api/runs",json={"text":"bad,header\n1,2"}).status_code==422
