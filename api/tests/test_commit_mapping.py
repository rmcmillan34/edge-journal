from fastapi.testclient import TestClient
from app.main import app
import io, csv, json

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_commit_with_override_mapping():
    email = "map_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    # CSV with non-standard headers that require override
    rows = [
        ["Acct","Instr","Direction","OpenTime","Qty","Entry","CloseTime","Exit","Commission","NetProfit","OrderID","Note"],
        ["Demo-1","EURUSD","buy","2025-05-01 08:00:00","1.00","1.10000","2025-05-01 09:00:00","1.10100","-2.00","80.00","T1","note"],
    ]
    data = make_csv(rows)
    override = json.dumps({
        "Account": "Acct",
        "Symbol": "Instr",
        "Side": "Direction",
        "Open Time": "OpenTime",
        "Close Time": "CloseTime",
        "Quantity": "Qty",
        "Entry Price": "Entry",
        "Exit Price": "Exit",
        "Fees": "Commission",
        "Net PnL": "NetProfit",
        "ExternalTradeID": "OrderID",
        "Notes": "Note",
    })

    files = {"file": ("custom.csv", data, "text/csv")}
    r = client.post("/uploads/commit", files=files, data={"mapping": override}, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    # Depending on prior tests, this may insert or update
    assert (j["inserted_count"] + j["updated_count"]) == 1
    assert not j["errors"]


def test_commit_with_preset_name():
    # Create user and preset, then commit using preset_name
    email = "preset_user@example.com"
    password = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": password})
    lr = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = lr.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    headers = ["Acct","Instr","Direction","OpenTime","Qty","Entry"]
    mapping = {
        "Account": "Acct",
        "Symbol": "Instr",
        "Side": "Direction",
        "Open Time": "OpenTime",
        "Quantity": "Qty",
        "Entry Price": "Entry",
    }
    body = {"name": "my-custom", "headers": headers, "mapping": mapping}
    pr = client.post("/presets", json=body, headers=auth)
    assert pr.status_code == 201, pr.text

    rows = [
        ["Acct","Instr","Direction","OpenTime","Qty","Entry"],
        ["Demo-1","EURUSD","Buy","2025-05-01 08:00:00","1.00","1.10000"],
    ]
    data = make_csv(rows)
    files = {"file": ("row.csv", data, "text/csv")}
    r = client.post("/uploads/commit", files=files, data={"preset_name": "my-custom"}, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert (j["inserted_count"] + j["updated_count"]) == 1
    assert not j["errors"]
