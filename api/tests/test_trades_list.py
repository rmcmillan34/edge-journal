from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_trades_list_after_commit():
    # auth
    email = "list_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    rows = [
        ["Account","Symbol","Side","Open Time","Close Time","Volume","Entry Price","Exit Price","Commission","Profit","Ticket","Comment"],
        ["Demo-List","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00","1.00","1.10000","1.10100","-2.00","80.00","TL1","note"],
        ["Demo-List","GBPUSD","Sell","2025-05-02 10:00:00","2025-05-02 10:10:00","0.50","1.25050","1.24900","-1.00","-75.00","TL2","note"],
    ]
    data = make_csv(rows)
    files = {"file": ("list.csv", data, "text/csv")}
    r1 = client.post("/uploads/commit", files=files, headers=auth)
    assert r1.status_code == 200, r1.text

    r2 = client.get("/trades?limit=10&offset=0", headers=auth)
    assert r2.status_code == 200
    items = r2.json()
    assert isinstance(items, list)
    assert any(t["symbol"] in ("EURUSD","GBPUSD") for t in items)
    # Minimal sanity on shape
    t0 = items[0]
    for key in ["id","account_name","symbol","side","open_time_utc"]:
        assert key in t0
