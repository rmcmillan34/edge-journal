from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)

def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()

def test_commit_inserts_and_dedups():
    rows = [
        ["Account","Symbol","Side","Open Time","Close Time","Volume","Entry Price","Exit Price","Commission","Profit","Ticket","Comment"],
        ["Demo-1","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00","1.00","1.10000","1.10100","-2.00","80.00","T1","note"],
        ["Demo-1","EURUSD","Sell","2025-05-02 10:00:00","2025-05-02 10:10:00","0.50","1.10050","1.09900","-1.00","-75.00","T2","note"],
    ]
    data = make_csv(rows)
    files = {"file": ("trades.csv", data, "text/csv")}
    r1 = client.post("/uploads/commit", files=files)
    assert r1.status_code == 200
    j1 = r1.json()

    # We may insert or update depending on DB state, but total affected rows should be 2 and no errors.
    assert (j1["inserted"] + j1["updated"]) == 2
    assert j1["skipped"] == 0
    assert not j1["errors"]

    r2 = client.post("/uploads/commit", files=files)
    assert r2.status_code == 200
    j2 = r2.json()

    # Accept either update-or-skip behavior; inserted must be 0
    assert j2["inserted"] == 0
    assert (j2["updated"] >= 2) or (j2["skipped"] >= 2)