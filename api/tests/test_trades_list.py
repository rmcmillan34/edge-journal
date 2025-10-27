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


def test_trades_list_with_filters():
    """Test trades list with filter DSL (M7 Phase 1)"""
    import json

    # auth
    email = "filter_list_user@example.com"
    pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}

    # Upload trades with different characteristics
    rows = [
        ["Account","Symbol","Side","Open Time","Close Time","Volume","Entry Price","Exit Price","Commission","Profit","Ticket","Comment"],
        ["Demo","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00","1.00","1.10000","1.10100","-2.00","100.00","F1","win"],
        ["Demo","GBPUSD","Sell","2025-05-02 10:00:00","2025-05-02 10:10:00","0.50","1.25050","1.24900","-1.00","-50.00","F2","loss"],
        ["Live","EURUSD","Buy","2025-05-03 12:00:00","2025-05-03 13:00:00","1.00","1.11000","1.11200","-2.00","150.00","F3","win"],
    ]
    data = make_csv(rows)
    files = {"file": ("filters.csv", data, "text/csv")}
    r1 = client.post("/uploads/commit", files=files, headers=auth)
    assert r1.status_code == 200, r1.text

    # Test 1: Filter by symbol
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "eq", "value": "EURUSD"}
        ]
    }
    r2 = client.get(f"/trades?filters={json.dumps(filter_dsl)}", headers=auth)
    assert r2.status_code == 200, r2.text
    items = r2.json()
    assert len(items) == 2
    assert all(t["symbol"] == "EURUSD" for t in items)

    # Test 2: Filter by net_pnl > 0 (winning trades)
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "gt", "value": 0}
        ]
    }
    r3 = client.get(f"/trades?filters={json.dumps(filter_dsl)}", headers=auth)
    assert r3.status_code == 200, r3.text
    items = r3.json()
    assert len(items) == 2  # 2 winning trades
    assert all(t["net_pnl"] > 0 for t in items)

    # Test 3: Complex filter with nested OR
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {
                "operator": "OR",
                "conditions": [
                    {"field": "account", "op": "eq", "value": "Demo"},
                    {"field": "net_pnl", "op": "gte", "value": 100}
                ]
            }
        ]
    }
    r4 = client.get(f"/trades?filters={json.dumps(filter_dsl)}", headers=auth)
    assert r4.status_code == 200, r4.text
    items = r4.json()
    assert len(items) >= 2  # At least Demo trades or high pnl trades
