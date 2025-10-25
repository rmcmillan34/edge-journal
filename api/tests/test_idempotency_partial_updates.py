from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_partial_updates_fill_exit_and_fees():
    email = "partial_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post(
        "/auth/login",
        data={"username": email, "password": pwd},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}

    # First commit: open only (no exit/fees)
    rows1 = [
        ["Account","Symbol","Side","Open Time","Quantity","Entry Price"],
        ["PA-ACC","EURUSD","Buy","2025-05-01 08:00:00","1.00","1.10000"],
    ]
    r1 = client.post("/uploads/commit", files={"file": ("open.csv", make_csv(rows1), "text/csv")}, headers=auth)
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert (j1["inserted_count"] + j1["updated_count"]) == 1

    # Second commit: same trade key, adds exit/fees/net
    rows2 = [
        ["Account","Symbol","Side","Open Time","Close Time","Quantity","Entry Price","Exit Price","Commission","Profit"],
        ["PA-ACC","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00","1.00","1.10000","1.10100","-2.00","80.00"],
    ]
    r2 = client.post("/uploads/commit", files={"file": ("exit.csv", make_csv(rows2), "text/csv")}, headers=auth)
    assert r2.status_code == 200, r2.text
    j2 = r2.json()
    assert j2["inserted_count"] == 0
    assert (j2["updated_count"] >= 1) or (j2["skipped_count"] >= 1)

    # Verify via trades list
    r3 = client.get("/trades?symbol=EURUSD", headers=auth)
    assert r3.status_code == 200
    items = r3.json()
    assert items and items[0]["exit_price"] is not None

