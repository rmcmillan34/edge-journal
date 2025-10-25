import os
os.environ.setdefault('ENV','dev')  # ensure alembic auto-migrations in tests

from fastapi.testclient import TestClient
from datetime import datetime
from app.main import app

client = TestClient(app)


def make_user_creds(idx: int = 0):
    return f"br{idx}_{datetime.utcnow().timestamp()}@example.com", "S3cretPwd!"


def auth_headers():
    email, password = make_user_creds()
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201
    lr = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert lr.status_code == 200
    token = lr.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_breach_created_on_risk_cap_exceed_and_acknowledge():
    auth = auth_headers()

    # Create playbook with tight template cap
    tpl_body = {
        "name": "PB-Cap",
        "purpose": "post",
        "schema": [
            {"key": "setup_ok", "label": "Setup OK", "type": "boolean", "required": True, "weight": 1},
            {"key": "intended_risk_pct", "label": "Risk %", "type": "number", "required": True, "weight": 1, "validation": {"min": 0, "max": 5}},
        ],
        "template_max_risk_pct": 0.5,
        "grade_thresholds": {"A": 0.9, "B": 0.75, "C": 0.6},
        "risk_schedule": {"A": 1.0, "B": 0.5, "C": 0.25, "D": 0.0},
    }
    r_tpl = client.post("/playbooks/templates", json=tpl_body, headers=auth)
    assert r_tpl.status_code == 200, r_tpl.text
    tpl = r_tpl.json()

    # Create a trade
    now = datetime.utcnow()
    t_body = {
        "symbol": "TEST",
        "side": "Buy",
        "open_time": now.isoformat() + "Z",
        "qty_units": 1,
        "entry_price": 10.0,
        "net_pnl": 1.0,
    }
    r_trade = client.post("/trades", json=t_body, headers=auth)
    assert r_trade.status_code == 201, r_trade.text
    trade_id = r_trade.json()["id"]

    # Save a response with intended risk exceeding template cap
    resp_body = {"template_id": tpl["id"], "values": {"setup_ok": True, "intended_risk_pct": 1.0}}
    r_resp = client.post(f"/trades/{trade_id}/playbook-responses", json=resp_body, headers=auth)
    assert r_resp.status_code == 200, r_resp.text

    # List breaches and find risk_cap_exceeded
    rb = client.get("/breaches?scope=trade", headers=auth)
    assert rb.status_code == 200, rb.text
    items = rb.json()
    assert any(b.get("rule_key") == "risk_cap_exceeded" for b in items)

    # Acknowledge the first one
    breach_id = items[0]["id"]
    ra = client.post(f"/breaches/{breach_id}/ack", headers=auth)
    assert ra.status_code == 200, ra.text
