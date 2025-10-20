from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def auth_pair():
    email = "journal_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def make_trade(auth, day: str):
    body = {
        "account_name": "J-ACC",
        "symbol": "EURUSD",
        "side": "Buy",
        "open_time": f"{day} 08:00:00",
        "qty_units": 1.0,
        "entry_price": 1.23456,
        "tz": "UTC",
    }
    r = client.post("/trades", json=body, headers=auth)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_daily_journal_crud_and_links():
    auth = auth_pair()
    d = "2025-05-02"
    tid1 = make_trade(auth, d)
    tid2 = make_trade(auth, d)

    # Not found initially
    r0 = client.get(f"/journal/{d}", headers=auth)
    assert r0.status_code == 404

    # Upsert create
    r1 = client.put(f"/journal/{d}", json={"title":"My Day","notes_md":"notes"}, headers=auth)
    assert r1.status_code == 200
    j = r1.json(); jid = j["id"]
    assert j["date"] == d and j["title"] == "My Day" and j["trade_ids"] == []

    # Link trades
    r2 = client.post(f"/journal/{jid}/trades", json=[tid1, tid2], headers=auth)
    assert r2.status_code == 200
    assert set(r2.json()["trade_ids"]) == {tid1, tid2}

    # Get
    r3 = client.get(f"/journal/{d}", headers=auth)
    assert r3.status_code == 200
    j2 = r3.json()
    assert set(j2["trade_ids"]) == {tid1, tid2}

    # Dates list
    r4 = client.get(f"/journal/dates?start={d}&end={d}", headers=auth)
    assert r4.status_code == 200
    assert d in r4.json()

