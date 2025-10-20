from fastapi.testclient import TestClient
from app.main import app
import io, csv, json

client = TestClient(app)


def make_csv(rows):
    buf = io.StringIO(); w = csv.writer(buf); w.writerows(rows); buf.seek(0); return buf.read()


def test_preview_basic_ok():
    rows = [
        [
            "Account","Symbol","Side","Open Time","Close Time",
            "Volume","Open Price","Close Price","Commission","Profit","Ticket","Comment"
        ],
        [
            "Demo-1","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00",
            "1.00","1.10000","1.10100","-2.00","80.00","T1","note"
        ],
    ]
    data = make_csv(rows)
    files = {"file": ("trades.csv", data, "text/csv")}
    r = client.post("/uploads/preview", files=files)
    assert r.status_code == 200
    j = r.json()
    assert "detected_preset" in j
    assert "applied_mapping" in j
    assert j["plan"]["rows_total"] == 1
    assert j["plan"]["rows_valid"] == 1
    assert j["plan"]["rows_invalid"] == 0
    assert len(j["preview"]) == 1


def test_preview_invalid_mapping_override_rejected():
    rows = [
        [
            "Account","Symbol","Side","Open Time","Close Time",
            "Volume","Open Price","Close Price","Commission","Profit","Ticket","Comment"
        ],
        [
            "Demo-1","EURUSD","Buy","2025-05-01 08:00:00","2025-05-01 09:00:00",
            "1.00","1.10000","1.10100","-2.00","80.00","T1","note"
        ],
    ]
    data = make_csv(rows)
    files = {"file": ("trades.csv", data, "text/csv")}
    # Force an invalid override that points to a header that doesn't exist
    override = json.dumps({"Account": "NoSuchHeader"})
    r = client.post("/uploads/preview", files=files, data={"mapping": override})
    assert r.status_code == 400
    j = r.json()
    assert "Mapping points to headers not present" in j["detail"]


def test_preview_missing_required_fields_returns_400():
    # Headers that don't map to required canonical fields
    rows = [
        ["Foo","Bar","Baz"],
        ["1","2","3"],
    ]
    data = make_csv(rows)
    files = {"file": ("bad.csv", data, "text/csv")}
    r = client.post("/uploads/preview", files=files)
    assert r.status_code == 400
    assert "Missing required canonical fields" in r.json()["detail"]

