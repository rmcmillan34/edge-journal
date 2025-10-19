import os
import shutil
import tempfile
import importlib
from fastapi.testclient import TestClient


# Minimal 1x1 PNG bytes (transparent)
MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_client(tmpdir: str) -> TestClient:
    # Ensure uploads go into a writable temp dir inside workspace
    os.environ["ATTACH_BASE_DIR"] = tmpdir
    # Reload app to pick up env var at import time
    if "app.main" in os.sys.modules:
        import app.routes_trades as routes_trades
        importlib.reload(routes_trades)
        import app.main as main
        importlib.reload(main)
        app = main.app
    else:
        from app.main import app  # type: ignore
    client = TestClient(app)
    return client


def register_and_login(client: TestClient):
    email = "attach_user@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post(
        "/auth/login",
        data={"username": email, "password": pwd},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def create_trade(client: TestClient, auth):
    body = {
        "account_name": "ATT-ACC",
        "symbol": "EURUSD",
        "side": "Buy",
        "open_time": "2025-01-01 10:00:00",
        "qty_units": 1.0,
        "entry_price": 1.23456,
        "tz": "UTC",
    }
    r = client.post("/trades", json=body, headers=auth)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_upload_png_and_thumb_and_download():
    tmpdir = tempfile.mkdtemp(prefix="ej_att_")
    try:
        client = make_client(tmpdir)
        auth = register_and_login(client)
        trade_id = create_trade(client, auth)

        files = {"file": ("tiny.png", MIN_PNG, "image/png")}
        data = {"timeframe": "M5", "state": "marked", "view": "entry", "caption": "tiny"}
        r = client.post(f"/trades/{trade_id}/attachments", headers=auth, files=files, data=data)
        assert r.status_code == 200, r.text
        att = r.json()
        assert att["filename"] == "tiny.png"

        # Always can download original
        att_id = att["id"]
        rd = client.get(f"/trades/{trade_id}/attachments/{att_id}/download", headers=auth)
        assert rd.status_code == 200

        # Thumbnail if Pillow is available; otherwise 404 is acceptable
        try:
            import PIL  # type: ignore
            pil_available = True
        except Exception:
            pil_available = False

        if pil_available:
            assert att.get("thumb_available") is True
            assert isinstance(att.get("thumb_url"), str) and att["thumb_url"].endswith("/thumb")
            rt = client.get(f"/trades/{trade_id}/attachments/{att_id}/thumb", headers=auth)
            assert rt.status_code == 200
            ctype = rt.headers.get("content-type", "")
            assert ctype.startswith("image/") and ("png" in ctype or "jpeg" in ctype)
        else:
            # No Pillow: the API falls back to raw save; thumb may not exist
            if att.get("thumb_available"):
                rt = client.get(f"/trades/{trade_id}/attachments/{att_id}/thumb", headers=auth)
                assert rt.status_code in (200, 404)
            else:
                rt = client.get(f"/trades/{trade_id}/attachments/{att_id}/thumb", headers=auth)
                assert rt.status_code == 404
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_upload_pdf_no_thumb():
    tmpdir = tempfile.mkdtemp(prefix="ej_att_")
    try:
        client = make_client(tmpdir)
        auth = register_and_login(client)
        trade_id = create_trade(client, auth)

        pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        files = {"file": ("doc.pdf", pdf_bytes, "application/pdf")}
        r = client.post(f"/trades/{trade_id}/attachments", headers=auth, files=files)
        assert r.status_code == 200, r.text
        att = r.json()
        assert att["filename"] == "doc.pdf"
        assert not att.get("thumb_available")
        # download ok
        att_id = att["id"]
        rd = client.get(f"/trades/{trade_id}/attachments/{att_id}/download", headers=auth)
        assert rd.status_code == 200
        # thumb should not exist
        rt = client.get(f"/trades/{trade_id}/attachments/{att_id}/thumb", headers=auth)
        assert rt.status_code == 404
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
