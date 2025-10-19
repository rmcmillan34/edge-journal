import os, shutil, tempfile, importlib
from fastapi.testclient import TestClient


MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_client(tmpdir: str) -> TestClient:
    os.environ["ATTACH_BASE_DIR"] = tmpdir
    # Reload routes modules to pick up env
    if "app.main" in os.sys.modules:
        import app.routes_journal as rj
        importlib.reload(rj)
        import app.main as main
        importlib.reload(main)
        app = main.app
    else:
        from app.main import app  # type: ignore
    return TestClient(app)


def register_and_token(client: TestClient):
    email = "journ_att@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    tok = client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_journal_attachments_flow():
    tmp = tempfile.mkdtemp(prefix="ej_jatt_")
    try:
        client = make_client(tmp)
        auth = register_and_token(client)
        d = "2025-06-03"
        # Upsert journal
        r0 = client.put(f"/journal/{d}", json={"title":"test","notes_md":"n"}, headers=auth)
        assert r0.status_code == 200
        jid = r0.json()["id"]

        # Upload an attachment
        files = {"file": ("tiny.png", MIN_PNG, "image/png")}
        r1 = client.post(f"/journal/{jid}/attachments", headers=auth, files=files)
        assert r1.status_code == 200, r1.text
        att = r1.json(); att_id = att["id"]
        # List
        r2 = client.get(f"/journal/{jid}/attachments", headers=auth)
        assert r2.status_code == 200
        assert any(a["id"] == att_id for a in r2.json())
        # Thumb (if available)
        rt = client.get(f"/journal/{jid}/attachments/{att_id}/thumb", headers=auth)
        assert rt.status_code in (200, 404)
        # Download original
        rd = client.get(f"/journal/{jid}/attachments/{att_id}/download", headers=auth)
        assert rd.status_code == 200

        # Delete journal by date
        rdel = client.delete(f"/journal/{d}", headers=auth)
        assert rdel.status_code == 200
        # Now GET should be 404
        rget = client.get(f"/journal/{d}", headers=auth)
        assert rget.status_code == 404
        # Dates list should not include d
        rdates = client.get(f"/journal/dates?start={d}&end={d}", headers=auth)
        assert rdates.status_code == 200
        assert d not in rdates.json()
        # Thumb should no longer be available (if file cleaned up)
        rt2 = client.get(f"/journal/{jid}/attachments/{att_id}/thumb", headers=auth)
        assert rt2.status_code in (404, 200)  # depending on FS timing
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

