from fastapi.testclient import TestClient
from app.main import app
import io, csv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_commit_with_timezone_conversion():
    # A unique symbol to query back
    sym = "TZTEST"
    local_tz = "Australia/Sydney"
    local_str = "2025-01-05 10:00:00"  # AEDT (UTC+11)
    dt_local = datetime.strptime(local_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo(local_tz))
    expected_utc = dt_local.astimezone(timezone.utc).isoformat()

    rows = [
        ["Symbol","Side","Open Time","Quantity","Entry Price"],
        [sym,"Buy",local_str,"1.00","1.23456"],
    ]
    data = make_csv(rows)
    files = {"file": ("tz.csv", data, "text/csv")}
    email = "tz_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    r = client.post("/uploads/commit", files=files, data={"account_name": "TZ-ACC", "tz": local_tz}, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert (j["inserted_count"] + j["updated_count"]) == 1

    # Verify via trades list
    r2 = client.get(f"/trades?symbol={sym}", headers=auth)
    assert r2.status_code == 200
    items = r2.json()
    assert items and items[0]["open_time_utc"].startswith(expected_utc[:19])  # compare seconds precision
