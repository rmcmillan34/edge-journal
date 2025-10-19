from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_metrics_summary_and_equity_curve():
    email = "metrics_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}`".replace('`','')}  # avoid backticks in header

    rows = [
        ["Account","Symbol","Side","Open Time","Close Time","Quantity","Entry Price","Exit Price","Profit"],
        ["M-ACC","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00","1.00","1.10000","1.10100","80.00"],
        ["M-ACC","EURUSD","Sell","2025-05-02 10:00:00","2025-05-02 10:10:00","0.50","1.10050","1.09900","-30.00"],
    ]
    data = make_csv(rows)
    r1 = client.post("/uploads/commit", files={"file": ("m.csv", data, "text/csv")}, headers=auth)
    assert r1.status_code == 200, r1.text

    r2 = client.get("/metrics", headers=auth)
    assert r2.status_code == 200
    j = r2.json()
    assert j["trades_total"] >= 2
    assert j["wins"] >= 1
    assert j["losses"] >= 1
    assert isinstance(j["net_pnl_sum"], float)
    ec = j["equity_curve"]
    assert isinstance(ec, list)
    if ec:
        assert set(["date","net_pnl","equity"]).issubset(ec[-1].keys())

