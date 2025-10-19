from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def make_user_creds():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    return email, "S3cretPwd!"


def test_auth_register_login_me():
    email, password = make_user_creds()

    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["email"] == email
    assert "id" in u

    r2 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r2.status_code == 200, r2.text
    tok = r2.json()
    assert tok["token_type"] == "bearer"
    assert tok["access_token"]

    r3 = client.get("/me", headers={"Authorization": f"Bearer {tok['access_token']}"})
    assert r3.status_code == 200
    me = r3.json()
    assert me["email"] == email


def test_presets_list_create_conflict():
    # Create user and login
    email, password = make_user_creds()
    client.post("/auth/register", json={"email": email, "password": password})
    lr = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = lr.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # List should be empty
    r0 = client.get("/presets", headers=auth)
    assert r0.status_code == 200
    assert r0.json() == []

    # Create preset
    headers = [
        "Account","Symbol","Side","Open Time","Close Time",
        "Volume","Open Price","Close Price","Commission","Profit","Ticket","Comment"
    ]
    mapping = {
        "Account": "Account",
        "Symbol": "Symbol",
        "Side": "Side",
        "Open Time": "Open Time",
        "Close Time": "Close Time",
        "Quantity": "Volume",
        "Entry Price": "Open Price",
        "Exit Price": "Close Price",
    }
    body = {"name": "ctrader-basic", "headers": headers, "mapping": mapping}
    r1 = client.post("/presets", json=body, headers=auth)
    assert r1.status_code == 201, r1.text
    p = r1.json()
    assert p["name"] == "ctrader-basic"
    assert p["headers"] == headers

    # Conflict on same name
    r2 = client.post("/presets", json=body, headers=auth)
    assert r2.status_code == 409

    # List should return one
    r3 = client.get("/presets", headers=auth)
    assert r3.status_code == 200
    assert len(r3.json()) >= 1

