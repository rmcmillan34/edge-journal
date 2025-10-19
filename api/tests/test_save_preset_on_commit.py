from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_commit_can_save_preset_name():
    email = "savepreset_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}

    rows = [
        ["Account","Symbol","Side","Open Time","Quantity","Entry Price"],
        ["SP-ACC","EURUSD","Buy","2025-05-01 08:00:00","1.00","1.10000"],
    ]
    data = make_csv(rows)
    files = {"file": ("sp.csv", data, "text/csv")}
    # Save mapping as preset "MyPreset" on commit
    r = client.post("/uploads/commit", files=files, data={"save_as": "MyPreset"}, headers=auth)
    assert r.status_code == 200, r.text

    # Should now list in /presets
    r2 = client.get("/presets", headers=auth)
    assert r2.status_code == 200
    lst = r2.json()
    assert any(p["name"] == "MyPreset" for p in lst)

