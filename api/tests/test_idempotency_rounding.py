from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_reupload_with_small_float_diffs_dedupes():
    email = "round_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    rows1 = [
        ["Account","Symbol","Side","Open Time","Quantity","Entry Price"],
        ["R-ACC","EURUSD","Buy","2025-05-01 08:00:00","1.0","1.100000"],
    ]
    rows2 = [
        ["Account","Symbol","Side","Open Time","Quantity","Entry Price"],
        ["R-ACC","EURUSD","Buy","2025-05-01 08:00:00","1.00","1.10000"],
    ]
    data1 = make_csv(rows1)
    data2 = make_csv(rows2)

    r1 = client.post("/uploads/commit", files={"file": ("a.csv", data1, "text/csv")}, headers=auth)
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert (j1["inserted"] + j1["updated"]) == 1

    r2 = client.post("/uploads/commit", files={"file": ("b.csv", data2, "text/csv")}, headers=auth)
    assert r2.status_code == 200, r2.text
    j2 = r2.json()
    assert j2["inserted"] == 0
    assert (j2["updated"] >= 1) or (j2["skipped"] >= 1)
