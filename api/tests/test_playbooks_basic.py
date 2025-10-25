from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app

client = TestClient(app)


def make_user_creds(idx: int = 0):
    return f"pbu{idx}_{datetime.utcnow().timestamp()}@example.com", "S3cretPwd!"


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


def test_playbook_template_create_evaluate_and_trade_response():
    auth = auth_headers()

    # Create a playbook template (post-trade)
    tpl_body = {
        "name": "PB-Post",
        "purpose": "post",
        "schema": [
            {"key": "setup_ok", "label": "Setup Criteria Met", "type": "boolean", "required": True, "weight": 1},
            {"key": "intended_risk_pct", "label": "Intended Risk %", "type": "number", "required": True, "weight": 1, "validation": {"min": 0, "max": 5}},
        ],
        "template_max_risk_pct": 1.0,
        "grade_thresholds": {"A": 0.9, "B": 0.75, "C": 0.6},
        "risk_schedule": {"A": 1.0, "B": 0.5, "C": 0.25, "D": 0.0},
    }
    r_tpl = client.post("/playbooks/templates", json=tpl_body, headers=auth)
    assert r_tpl.status_code == 200, r_tpl.text
    tpl = r_tpl.json()
    assert tpl["name"] == "PB-Post"

    # Create a trade (manual)
    now = datetime.utcnow()
    t_body = {
        "symbol": "TEST",
        "side": "Buy",
        "open_time": now.isoformat() + "Z",
        "qty_units": 1,
        "entry_price": 10.0,
        "net_pnl": 1.23,
    }
    r_trade = client.post("/trades", json=t_body, headers=auth)
    assert r_trade.status_code == 201, r_trade.text
    trade = r_trade.json()
    trade_id = trade["id"]

    # Evaluate values
    eval_body = {"template_id": tpl["id"], "values": {"setup_ok": True, "intended_risk_pct": 0.75}}
    r_eval = client.post("/playbooks/evaluate", json=eval_body, headers=auth)
    assert r_eval.status_code == 200, r_eval.text
    ev = r_eval.json()
    assert ev["grade"] in ["A","B","C","D"]
    assert isinstance(ev["risk_cap_pct"], (int,float))

    # Save a response
    resp_body = {"template_id": tpl["id"], "values": {"setup_ok": True, "intended_risk_pct": 1.2}, "comments": {"setup_ok": "looks good"}}
    r_resp = client.post(f"/trades/{trade_id}/playbook-responses", json=resp_body, headers=auth)
    assert r_resp.status_code == 200, r_resp.text
    pr = r_resp.json()
    assert pr["template_id"] == tpl["id"]

    # List responses for trade
    r_list = client.get(f"/trades/{trade_id}/playbook-responses", headers=auth)
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) >= 1


def test_trading_rules_defaults_and_update():
    auth = auth_headers()
    # Defaults
    r0 = client.get("/settings/trading-rules", headers=auth)
    assert r0.status_code == 200
    d = r0.json()
    assert d["max_losses_row_day"] >= 1

    # Update
    body = {
        "max_losses_row_day": 2,
        "max_losing_days_streak_week": 2,
        "max_losing_weeks_streak_month": 1,
        "alerts_enabled": True,
    }
    r1 = client.put("/settings/trading-rules", json=body, headers=auth)
    assert r1.status_code == 200
    r2 = client.get("/settings/trading-rules", headers=auth)
    assert r2.json()["max_losses_row_day"] == 2


def test_calendar_breaches_endpoint():
    auth = auth_headers()
    today = datetime.utcnow().date()
    start = today.replace(day=1)
    end = today
    r = client.get(f"/metrics/calendar?start={start.isoformat()}&end={end.isoformat()}", headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "days" in j
    assert isinstance(j["days"], list)


def test_playbook_evidence_crud_for_trade():
    auth = auth_headers()

    # Create playbook template
    tpl_body = {
        "name": "PB-Evidence",
        "purpose": "post",
        "schema": [
            {"key": "setup_ok", "label": "Setup OK", "type": "boolean", "required": True, "weight": 1},
            {"key": "link_field", "label": "Link Field", "type": "text", "required": False, "weight": 1},
        ],
        "template_max_risk_pct": 1.0,
    }
    r_tpl = client.post("/playbooks/templates", json=tpl_body, headers=auth)
    assert r_tpl.status_code == 200, r_tpl.text
    tpl = r_tpl.json()

    # Create a trade
    now = datetime.utcnow()
    t_body = {
        "symbol": "EV",
        "side": "Buy",
        "open_time": now.isoformat() + "Z",
        "qty_units": 1,
        "entry_price": 10.0,
        "net_pnl": 0.5,
    }
    r_trade = client.post("/trades", json=t_body, headers=auth)
    assert r_trade.status_code == 201, r_trade.text
    trade_id = r_trade.json()["id"]

    # Save a response to attach evidence to
    resp_body = {"template_id": tpl["id"], "values": {"setup_ok": True, "link_field": "ref"}}
    r_resp = client.post(f"/trades/{trade_id}/playbook-responses", json=resp_body, headers=auth)
    assert r_resp.status_code == 200, r_resp.text
    resp_id = r_resp.json()["id"]

    # Add URL evidence
    ev_body = {"field_key": "link_field", "source_kind": "url", "url": "https://example.com", "note": "proof"}
    r_ev = client.post(f"/playbook-responses/{resp_id}/evidence", json=ev_body, headers=auth)
    assert r_ev.status_code == 200, r_ev.text
    ev = r_ev.json()
    assert ev["field_key"] == "link_field"

    # List evidence
    r_list = client.get(f"/playbook-responses/{resp_id}/evidence", headers=auth)
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) >= 1

    # Delete evidence
    r_del = client.delete(f"/playbook-responses/{resp_id}/evidence/{ev['id']}", headers=auth)
    assert r_del.status_code == 200, r_del.text
    r_list2 = client.get(f"/playbook-responses/{resp_id}/evidence", headers=auth)
    assert r_list2.status_code == 200
    items2 = r_list2.json()
    assert all(i["id"] != ev["id"] for i in items2)


def test_instrument_checklist_crud_in_journal():
    auth = auth_headers()

    # Create a pre-trade playbook
    tpl_body = {
        "name": "PB-Pre",
        "purpose": "pre",
        "schema": [
            {"key": "symbol", "label": "Symbol", "type": "text", "required": True, "weight": 1},
            {"key": "ready", "label": "Ready", "type": "boolean", "required": True, "weight": 1},
        ],
    }
    r_tpl = client.post("/playbooks/templates", json=tpl_body, headers=auth)
    assert r_tpl.status_code == 200, r_tpl.text
    tpl = r_tpl.json()

    # Ensure a journal exists for today
    today = datetime.utcnow().date().isoformat()
    client.put(f"/journal/{today}", json={"title": "Test", "notes_md": ""}, headers=auth)

    # Upsert checklist for symbol
    body = {"template_id": tpl["id"], "values": {"symbol": "EURUSD", "ready": True}}
    r_up = client.post(f"/journal/{today}/instrument/EURUSD/playbook-response", json=body, headers=auth)
    assert r_up.status_code == 200, r_up.text
    resp = r_up.json()
    assert resp["template_id"] == tpl["id"]

    # Get latest for symbol
    r_get = client.get(f"/journal/{today}/instrument/EURUSD/playbook-response", headers=auth)
    assert r_get.status_code == 200, r_get.text
    got = r_get.json()
    assert got and got["values"].get("symbol") == "EURUSD"

    # List all for date/symbol
    r_list = client.get(f"/journal/{today}/instrument/EURUSD/playbook-responses", headers=auth)
    assert r_list.status_code == 200
    assert isinstance(r_list.json(), list)
