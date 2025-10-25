from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)


def test_ftmo_like_headers_with_duplicate_price_columns_commit_with_fallback_account():
    # Header row modeled after docs/examples/ftmo-example-trades.csv
    header = [
        "Ticket","Open","Type","Volume","Symbol","Price","SL","TP","Close","Price","Swap","Commissions","Profit","Pips","Trade duration in seconds"
    ]
    row = [
        "T1","2025-10-17 07:49:37","buy","1.00","GBPUSD","1.34500","0","0","2025-10-17 08:05:36","1.34600","0","-12.1","142.78","5.9","959"
    ]
    csv_text = ",".join(header) + "\n" + ",".join(row) + "\n"
    files = {"file": ("ftmo.csv", csv_text, "text/csv")}

    # Commit with fallback account; should not error and insert/update one row
    # auth
    email = "ftmo_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}
    r = client.post("/uploads/commit", files=files, data={"account_name": "FTMO-25K"}, headers=auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert (j["inserted_count"] + j["updated_count"]) == 1
    assert not j["errors"]
