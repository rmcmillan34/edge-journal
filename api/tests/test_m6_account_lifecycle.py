"""
Tests for M6: Account Lifecycle (close/reopen)
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def register_and_login() -> str:
    """Helper to register a user and return token"""
    email = f"m6_lifecycle_{id(client)}@example.com"
    client.post("/auth/register", json={"email": email, "password": "password123"})
    resp = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_close_account():
    """Test closing an account with reason and note"""
    token = register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create account with unique name
    import time
    account_name = f"TestAccount_{int(time.time() * 1000000)}"
    resp = client.post("/accounts", headers=headers, json={"name": account_name, "broker_label": "Broker1"})
    assert resp.status_code == 201
    account_id = resp.json()["id"]
    assert resp.json()["status"] == "active"

    # Close account
    resp = client.post(
        f"/accounts/{account_id}/close",
        headers=headers,
        json={"reason": "breach", "note": "Daily loss limit exceeded"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"
    assert data["close_reason"] == "breach"
    assert data["close_note"] == "Daily loss limit exceeded"
    assert data["closed_at"] is not None


def test_close_already_closed_account():
    """Test that closing an already closed account returns 400"""
    token = register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create and close account with unique name
    import time
    account_name = f"TestAccount_{int(time.time() * 1000000)}"
    resp = client.post("/accounts", headers=headers, json={"name": account_name})
    account_id = resp.json()["id"]
    client.post(f"/accounts/{account_id}/close", headers=headers, json={"reason": "retired"})

    # Try to close again
    resp = client.post(f"/accounts/{account_id}/close", headers=headers, json={"reason": "breach"})
    assert resp.status_code == 400
    assert "already closed" in resp.json()["detail"].lower()


def test_reopen_account():
    """Test reopening a closed account"""
    token = register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create and close account with unique name
    import time
    account_name = f"TestAccount_{int(time.time() * 1000000)}"
    resp = client.post("/accounts", headers=headers, json={"name": account_name})
    account_id = resp.json()["id"]
    client.post(f"/accounts/{account_id}/close", headers=headers, json={"reason": "breach", "note": "Blown"})

    # Reopen account
    resp = client.post(
        f"/accounts/{account_id}/reopen",
        headers=headers,
        json={"note": "Back from challenge reset"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    # closed_at and close_reason should be preserved for audit
    assert data["closed_at"] is not None
    assert data["close_reason"] == "breach"
    # Reopen note should be appended
    assert "Reopened" in data["close_note"]
    assert "Back from challenge reset" in data["close_note"]


def test_reopen_active_account():
    """Test that reopening an active account returns 400"""
    token = register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create account (active by default) with unique name
    import time
    account_name = f"TestAccount_{int(time.time() * 1000000)}"
    resp = client.post("/accounts", headers=headers, json={"name": account_name})
    account_id = resp.json()["id"]

    # Try to reopen
    resp = client.post(f"/accounts/{account_id}/reopen", headers=headers, json={})
    assert resp.status_code == 400
    assert "not closed" in resp.json()["detail"].lower()


def test_list_accounts_include_closed():
    """Test that closed accounts are excluded by default but included with flag"""
    token = register_and_login()
    headers = {"Authorization": f"Bearer {token}"}

    # Create two accounts with unique names, close one
    import time
    t = int(time.time() * 1000000)
    resp1 = client.post("/accounts", headers=headers, json={"name": f"Active_{t}"})
    resp2 = client.post("/accounts", headers=headers, json={"name": f"Closed_{t}"})
    closed_id = resp2.json()["id"]
    client.post(f"/accounts/{closed_id}/close", headers=headers, json={"reason": "retired"})

    # List without include_closed (default) - should only get active accounts
    resp = client.get("/accounts", headers=headers)
    assert resp.status_code == 200
    accounts = resp.json()
    names = [a["name"] for a in accounts]
    # Closed account should NOT be in the list
    assert not any(n.startswith("Closed_") and str(t) in n for n in names)
    # Active account should be in the list
    assert any(n.startswith("Active_") and str(t) in n for n in names)

    # List with include_closed=true - should get both
    resp = client.get("/accounts?include_closed=true", headers=headers)
    assert resp.status_code == 200
    accounts_all = resp.json()
    names_all = [a["name"] for a in accounts_all]
    # Both accounts should be present
    assert any(n.startswith("Active_") and str(t) in n for n in names_all)
    assert any(n.startswith("Closed_") and str(t) in n for n in names_all)
