from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_commit_without_account_header_uses_default_account():
    email = "defacct_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    rows = [
        ["Symbol","Side","Open Time","Quantity","Entry Price"],
        ["EURUSD","Buy","2025-05-01 08:00:00","1.00","1.10000"],
    ]
    data = make_csv(rows)
    files = {"file": ("noacct.csv", data, "text/csv")}
    r = client.post("/uploads/commit", files=files, data={"account_name": "FTMO-25K"}, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert (j["inserted_count"] + j["updated_count"]) == 1
    assert not j["errors"]
