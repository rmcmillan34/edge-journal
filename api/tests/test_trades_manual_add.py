from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_trade_manual():
    email = "manual_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}

    # Create trade
    payload = {
        "account_name": "MAN-ACC",
        "symbol": "XAUUSD",
        "side": "Buy",
        "open_time": "2025-05-01 08:00:00",
        "close_time": "2025-05-01 09:00:00",
        "qty_units": 1.0,
        "entry_price": 2300.0,
        "exit_price": 2301.0,
        "fees": -2.0,
        "net_pnl": 98.0,
        "notes_md": "manual entry",
        "tz": "UTC",
    }
    r = client.post("/trades", json=payload, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["symbol"] == "XAUUSD"
    assert j["account_name"] == "MAN-ACC"

    # List by date
    r2 = client.get("/trades?start=2025-05-01&end=2025-05-01", headers=auth)
    assert r2.status_code == 200
    items = r2.json()
    assert any(t["symbol"] == "XAUUSD" for t in items)

