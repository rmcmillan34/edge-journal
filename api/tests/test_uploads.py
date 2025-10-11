# api/tests/test_uploads.py
from fastapi.testclient import TestClient
from app.main import app
import io, csv

client = TestClient(app)

def test_csv_upload_dry_run():
    # Small cTrader-like CSV in memory
    rows = [
        ["Account","Symbol","Side","Open Time","Close Time","Volume","Open Price","Close Price","Commission","Profit","Ticket","Comment"],
        ["FTMO-25K","GBPUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00","0.50","1.25000","1.25250","-3.50","125.00","123456","A-note"],
        ["FTMO-25K","GBPUSD","Sell","2025-05-02 10:00:00","2025-05-02 10:15:00","0.30","1.25100","1.24900","-2.10","-63.00","123457","B-note"],
    ]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows(rows)
    buf.seek(0)

    files = {"file": ("trades.csv", buf.read(), "text/csv")}
    r = client.post("/uploads", files=files)
    assert r.status_code == 200
    data = r.json()
    assert "detected_preset" in data
    assert data["plan"]["rows_total"] == 2
    assert len(data["preview"]) == 2
    assert "Symbol" in data["mapping"]
