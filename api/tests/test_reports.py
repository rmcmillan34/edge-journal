"""
Tests for PDF report generation endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)


def register_and_login():
    """Helper function to register a user and get auth token."""
    import uuid
    email = f"reporttest_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "TestPwd123!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    r = client.post("/auth/login", data={"username": email, "password": pwd})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_monthly_report():
    """Test that monthly report generation returns PDF."""
    auth = register_and_login()

    payload = {
        "type": "monthly",
        "period": {
            "year": 2025,
            "month": 1
        },
        "theme": "light",
        "include_screenshots": False
    }

    r = client.post("/api/reports/generate", json=payload, headers=auth)
    # Should return 200 with PDF content
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"  # PDF magic bytes
    assert len(r.content) > 1000  # Should have substantial content


def test_generate_report_missing_period():
    """Test that missing period fields return 400."""
    auth = register_and_login()

    # Monthly report without year/month
    payload = {
        "type": "monthly",
        "period": {},
        "theme": "light"
    }

    r = client.post("/api/reports/generate", json=payload, headers=auth)
    assert r.status_code == 400
    assert "required" in r.json()["detail"].lower()


def test_generate_report_invalid_type():
    """Test that invalid report type returns 400."""
    auth = register_and_login()

    payload = {
        "type": "invalid_type",
        "period": {"year": 2025, "month": 1}
    }

    # This should fail validation at Pydantic level
    r = client.post("/api/reports/generate", json=payload, headers=auth)
    assert r.status_code == 422  # Unprocessable entity


def test_list_report_history_empty():
    """Test that listing report history works for new user."""
    auth = register_and_login()

    r = client.get("/api/reports/history", headers=auth)
    assert r.status_code == 200
    reports = r.json()
    assert isinstance(reports, list)
    assert len(reports) == 0  # New user should have no reports


def test_report_requires_auth():
    """Test that report endpoints require authentication."""
    # Try without auth header
    r = client.post("/api/reports/generate", json={
        "type": "monthly",
        "period": {"year": 2025, "month": 1}
    })
    assert r.status_code == 401

    r = client.get("/api/reports/history")
    assert r.status_code == 401


def test_download_report_not_found():
    """Test that downloading non-existent report returns 404."""
    auth = register_and_login()

    r = client.get("/api/reports/download/nonexistent.pdf", headers=auth)
    assert r.status_code == 404


def test_download_report_path_traversal():
    """Test that path traversal in filename is blocked."""
    auth = register_and_login()

    # Try path traversal
    r = client.get("/api/reports/download/../../../etc/passwd", headers=auth)
    # FastAPI routing may return 404 (route not matched) or 400 (security check)
    # Both are acceptable for security
    assert r.status_code in [400, 404]


def test_delete_report_not_found():
    """Test that deleting non-existent report returns 404."""
    auth = register_and_login()

    r = client.delete("/api/reports/nonexistent.pdf", headers=auth)
    assert r.status_code == 404


def test_delete_report_path_traversal():
    """Test that path traversal in filename is blocked for delete."""
    auth = register_and_login()

    # Try path traversal
    r = client.delete("/api/reports/../../../etc/passwd", headers=auth)
    # FastAPI routing may return 404 (route not matched) or 400 (security check)
    # Both are acceptable for security
    assert r.status_code in [400, 404]


def test_metrics_calculation_empty():
    """Test metrics calculation with no trades."""
    from app.reports import ReportGenerator
    from app.db import SessionLocal

    db = SessionLocal()
    generator = ReportGenerator(db, user_id=1)

    metrics = generator.calculate_metrics([])

    assert metrics["total_pnl"] == 0.0
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["profit_factor"] == 0.0

    db.close()


def test_metrics_calculation_with_trades():
    """Test metrics calculation with mock trades."""
    from app.reports import ReportGenerator
    from app.db import SessionLocal
    from app.models import Trade
    from decimal import Decimal

    db = SessionLocal()
    generator = ReportGenerator(db, user_id=1)

    # Create mock trades
    class MockTrade:
        def __init__(self, net_pnl):
            self.net_pnl = Decimal(str(net_pnl)) if net_pnl is not None else None

    trades = [
        MockTrade(100.0),   # Win
        MockTrade(-50.0),   # Loss
        MockTrade(150.0),   # Win
        MockTrade(-30.0),   # Loss
        MockTrade(80.0),    # Win
    ]

    metrics = generator.calculate_metrics(trades)

    assert metrics["total_pnl"] == 250.0  # 100 - 50 + 150 - 30 + 80
    assert metrics["total_trades"] == 5
    assert metrics["winning_trades"] == 3
    assert metrics["losing_trades"] == 2
    assert metrics["win_rate"] == 0.6  # 3/5
    assert metrics["avg_win"] == 110.0  # (100 + 150 + 80) / 3
    assert metrics["avg_loss"] == 40.0  # (50 + 30) / 2
    assert metrics["largest_win"] == 150.0
    assert metrics["largest_loss"] == -50.0
    assert metrics["profit_factor"] == round(330.0 / 80.0, 2)  # sum(wins) / abs(sum(losses))

    db.close()
