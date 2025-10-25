"""
Unit tests for filter DSL compiler (M7 Phase 1)

Tests cover:
- Individual operators (eq, ne, contains, in, not_in, gte, lte, gt, lt, between, is_null, not_null)
- Nested AND/OR groups
- Playbook field joins
- Date/time parsing
- Error handling for invalid filters
"""

from fastapi.testclient import TestClient
from app.main import app
import io
import csv
import json

client = TestClient(app)


def make_csv(rows):
    """Helper to create CSV content from rows"""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows(rows)
    buf.seek(0)
    return buf.read()


def register_and_login():
    """Helper to register a user and get auth token"""
    email = f"filter_test_{id(client)}@example.com"
    pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok_resp = client.post(
        "/auth/login",
        data={"username": email, "password": pwd},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = tok_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_test_trades(auth):
    """Helper to upload test trades via CSV"""
    rows = [
        ["Account", "Symbol", "Side", "Open Time", "Close Time", "Volume", "Entry Price", "Exit Price", "Commission", "Profit", "Ticket", "Comment"],
        ["Demo", "EURUSD", "Buy", "2025-01-01 08:00:00", "2025-01-01 09:00:00", "1.00", "1.10000", "1.10100", "-2.00", "100.00", "T1", "win"],
        ["Demo", "GBPUSD", "Sell", "2025-01-02 10:00:00", "2025-01-02 10:10:00", "0.50", "1.25050", "1.24900", "-1.00", "-50.00", "T2", "loss"],
        ["Demo", "USDJPY", "Buy", "2025-01-03 12:00:00", "2025-01-03 13:00:00", "1.00", "110.000", "110.100", "-2.00", "80.00", "T3", "win"],
        ["Live", "EURUSD", "Buy", "2025-01-04 08:00:00", "2025-01-04 09:00:00", "1.00", "1.11000", "1.11200", "-3.00", "150.00", "T4", "win"],
        ["Live", "AUDUSD", "Sell", "2025-01-05 10:00:00", "2025-01-05 11:00:00", "1.00", "0.65000", "0.64900", "-2.00", "-100.00", "T5", "loss"],
    ]
    data = make_csv(rows)
    files = {"file": ("test.csv", data, "text/csv")}
    r = client.post("/uploads/commit", files=files, headers=auth)
    assert r.status_code == 200, r.text


def test_filter_eq_operator():
    """Test 'eq' operator for exact matches"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by symbol equals EURUSD
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "eq", "value": "EURUSD"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 2  # 2 EURUSD trades
    assert all(t["symbol"] == "EURUSD" for t in trades)


def test_filter_ne_operator():
    """Test 'ne' operator for not equals"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter for symbols not equal to EURUSD
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "ne", "value": "EURUSD"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(t["symbol"] != "EURUSD" for t in trades)


def test_filter_contains_operator():
    """Test 'contains' operator for substring matching"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by symbol contains 'USD'
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "contains", "value": "USD"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) >= 4  # EURUSD, GBPUSD, USDJPY, AUDUSD
    assert all("USD" in (t["symbol"] or "") for t in trades)


def test_filter_in_operator():
    """Test 'in' operator for list matching"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by symbol in [EURUSD, GBPUSD]
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "in", "value": ["EURUSD", "GBPUSD"]}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 3  # 2 EURUSD + 1 GBPUSD
    assert all(t["symbol"] in ["EURUSD", "GBPUSD"] for t in trades)


def test_filter_not_in_operator():
    """Test 'not_in' operator"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by symbol not in [EURUSD, GBPUSD]
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "not_in", "value": ["EURUSD", "GBPUSD"]}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(t["symbol"] not in ["EURUSD", "GBPUSD"] for t in trades)


def test_filter_gte_operator():
    """Test 'gte' operator for numeric comparison"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl >= 0 (winning trades)
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "gte", "value": 0}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 3  # 3 winning trades
    assert all(t["net_pnl"] >= 0 for t in trades)


def test_filter_lte_operator():
    """Test 'lte' operator for numeric comparison"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl <= 0 (losing trades and breakeven)
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "lte", "value": 0}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(t["net_pnl"] <= 0 for t in trades)


def test_filter_gt_operator():
    """Test 'gt' operator"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl > 100
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "gt", "value": 100}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(t["net_pnl"] > 100 for t in trades)


def test_filter_lt_operator():
    """Test 'lt' operator"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl < 0 (only losses)
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "lt", "value": 0}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(t["net_pnl"] < 0 for t in trades)


def test_filter_between_operator():
    """Test 'between' operator for range queries"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl between 50 and 150
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "between", "value": [50, 150]}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(50 <= t["net_pnl"] <= 150 for t in trades)


def test_filter_between_dates():
    """Test 'between' operator with dates"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by open_time between 2025-01-01 and 2025-01-04
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "open_time", "op": "between", "value": ["2025-01-01", "2025-01-04"]}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 4  # Jan 1, 2, 3, 4


def test_filter_is_null_operator():
    """Test 'is_null' operator"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter for trades without close_time (shouldn't exist in our test data)
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "close_time", "op": "is_null"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    # All our test trades have close times
    assert len(trades) == 0


def test_filter_not_null_operator():
    """Test 'not_null' operator"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter for trades with close_time
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "close_time", "op": "not_null"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 5  # All trades have close times
    assert all(t["close_time_utc"] is not None for t in trades)


def test_filter_nested_and_groups():
    """Test nested AND groups"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter: symbol contains USD AND net_pnl > 0
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "contains", "value": "USD"},
            {"field": "net_pnl", "op": "gt", "value": 0}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all("USD" in t["symbol"] and t["net_pnl"] > 0 for t in trades)


def test_filter_nested_or_groups():
    """Test nested OR groups"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter: symbol = EURUSD OR symbol = GBPUSD
    filter_dsl = {
        "operator": "OR",
        "conditions": [
            {"field": "symbol", "op": "eq", "value": "EURUSD"},
            {"field": "symbol", "op": "eq", "value": "GBPUSD"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 3  # 2 EURUSD + 1 GBPUSD
    assert all(t["symbol"] in ["EURUSD", "GBPUSD"] for t in trades)


def test_filter_complex_nested_groups():
    """Test complex nested AND/OR groups"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter: (symbol = EURUSD OR symbol = GBPUSD) AND net_pnl > 0
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {
                "operator": "OR",
                "conditions": [
                    {"field": "symbol", "op": "eq", "value": "EURUSD"},
                    {"field": "symbol", "op": "eq", "value": "GBPUSD"}
                ]
            },
            {"field": "net_pnl", "op": "gt", "value": 0}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all(
        t["symbol"] in ["EURUSD", "GBPUSD"] and t["net_pnl"] > 0
        for t in trades
    )


def test_filter_account_field():
    """Test filtering by account name"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by account = Demo
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "account", "op": "eq", "value": "Demo"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 3  # 3 Demo account trades
    assert all(t["account_name"] == "Demo" for t in trades)


def test_filter_with_pagination():
    """Test that filters work correctly with pagination"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl > 0 with pagination
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "gt", "value": 0}
        ]
    }

    # Page 1
    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}&limit=2&offset=0",
        headers=auth
    )
    assert r.status_code == 200, r.text
    page1 = r.json()
    assert len(page1) == 2
    assert all(t["net_pnl"] > 0 for t in page1)

    # Page 2
    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}&limit=2&offset=2",
        headers=auth
    )
    assert r.status_code == 200, r.text
    page2 = r.json()
    assert len(page2) >= 1
    assert all(t["net_pnl"] > 0 for t in page2)


def test_filter_with_sorting():
    """Test that filters work correctly with sorting"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Filter by net_pnl > 0, sorted by net_pnl descending
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "net_pnl", "op": "gt", "value": 0}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}&sort=net_pnl:desc",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()

    # Check all are positive
    assert all(t["net_pnl"] > 0 for t in trades)

    # Check sorting (descending)
    pnls = [t["net_pnl"] for t in trades]
    assert pnls == sorted(pnls, reverse=True)


def test_filter_invalid_json():
    """Test error handling for invalid filter JSON"""
    auth = register_and_login()

    # Invalid JSON
    r = client.get(
        "/trades?filters={invalid json}",
        headers=auth
    )
    assert r.status_code == 400
    assert "Invalid filter JSON" in r.json()["detail"]


def test_filter_unknown_field():
    """Test error handling for unknown filter field"""
    auth = register_and_login()

    # Unknown field
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "unknown_field", "op": "eq", "value": "test"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 400
    assert "Unknown filter field" in r.json()["detail"]


def test_filter_invalid_operator():
    """Test error handling for invalid operator"""
    auth = register_and_login()

    # Invalid operator
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "invalid_op", "value": "test"}
        ]
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 400
    assert "Unknown operator" in r.json()["detail"]


def test_legacy_params_backward_compatibility():
    """Test that legacy query params still work (backward compatibility)"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Test legacy symbol param
    r = client.get("/trades?symbol=EURUSD", headers=auth)
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all("EURUSD" in (t["symbol"] or "") for t in trades)

    # Test legacy account param
    r = client.get("/trades?account=Demo", headers=auth)
    assert r.status_code == 200, r.text
    trades = r.json()
    assert all("Demo" in (t["account_name"] or "") for t in trades)

    # Test legacy date params
    r = client.get("/trades?start=2025-01-01&end=2025-01-03", headers=auth)
    assert r.status_code == 200, r.text
    trades = r.json()
    # Should return trades on Jan 1, 2, and 3 (up to but not including end date logic)
    assert len(trades) >= 2


def test_filter_empty_conditions():
    """Test filter with empty conditions returns all trades"""
    auth = register_and_login()
    upload_test_trades(auth)

    # Empty conditions
    filter_dsl = {
        "operator": "AND",
        "conditions": []
    }

    r = client.get(
        f"/trades?filters={json.dumps(filter_dsl)}",
        headers=auth
    )
    assert r.status_code == 200, r.text
    trades = r.json()
    assert len(trades) == 5  # All trades returned
