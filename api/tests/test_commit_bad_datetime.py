from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)

def make_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows(rows)
    buf.seek(0)
    return buf.read()

def test_commit_handles_bad_datetime():
    rows = [
        ["Account","Symbol","Side","Open Time","Close Time","Volume","Entry Price","Exit Price","Commission","Profit","Ticket","Comment"],
        ["Demo-1","EURUSD","Buy","NOT A DATE","2025-05-01 09:00:00","1.00","1.10000","1.10100","-2.00","80.00","T1","note"],
    ]
    data = make_csv(rows)
    files = {"file": ("bad.csv", data, "text/csv")}
    r = client.post("/uploads/commit", files=files)
    assert r.status_code == 200
    j = r.json()
    assert j["errors"] and "datetime" in j["errors"][0]["reason"].lower()
