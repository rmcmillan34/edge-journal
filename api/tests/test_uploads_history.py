from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_uploads_history_lists_summary_counts():
    email = "hist_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    rows = [
        ["Account","Symbol","Side","Open Time","Quantity","Entry Price"],
        ["HIST-ACC","EURUSD","Buy","2025-05-01 08:00:00","1.00","1.10000"],
    ]
    data = make_csv(rows)
    r = client.post("/uploads/commit", files={"file": ("hist.csv", data, "text/csv")}, headers=auth)
    assert r.status_code == 200
    j = r.json()
    uid = j["upload_id"]

    r2 = client.get("/uploads", headers=auth)
    assert r2.status_code == 200
    lst = r2.json()
    assert any(u["id"] == uid for u in lst)
    rec = next(u for u in lst if u["id"] == uid)
    assert rec["inserted_count"] >= 1
    assert rec["error_count"] == 0
