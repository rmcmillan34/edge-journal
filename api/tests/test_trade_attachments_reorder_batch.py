import os, shutil, tempfile, importlib
from fastapi.testclient import TestClient

MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def mkclient(tmpdir: str) -> TestClient:
    os.environ["ATTACH_BASE_DIR"] = tmpdir
    if "app.main" in os.sys.modules:
        import app.routes_trades as rt
        importlib.reload(rt)
        import app.main as main
        importlib.reload(main)
        app = main.app
    else:
        from app.main import app  # type: ignore
    return TestClient(app)


def token(client: TestClient):
    email = "att_reorder@example.com"; pwd = "S3cretPwd!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    return client.post("/auth/login", data={"username": email, "password": pwd}, headers={"Content-Type":"application/x-www-form-urlencoded"}).json()["access_token"]


def mk_trade(client: TestClient, tok: str):
    auth = {"Authorization": f"Bearer {tok}"}
    body = {"account_name":"A","symbol":"EURUSD","side":"Buy","open_time":"2025-01-01 00:00:00","qty_units":1.0,"entry_price":1.1,"tz":"UTC"}
    r = client.post("/trades", json=body, headers=auth)
    assert r.status_code == 200
    return r.json()["id"], auth


def upload(client: TestClient, auth, trade_id: int, name: str):
    files = {"file": (name, MIN_PNG, "image/png")}
    r = client.post(f"/trades/{trade_id}/attachments", headers=auth, files=files)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def list_ids(client: TestClient, auth, trade_id: int):
    r = client.get(f"/trades/{trade_id}/attachments", headers=auth)
    assert r.status_code == 200
    return [a["id"] for a in r.json()]


def test_reorder_and_batch_delete():
    tmp = tempfile.mkdtemp(prefix="ej_tatt_")
    try:
        client = mkclient(tmp)
        tok = token(client)
        trade_id, auth = mk_trade(client, tok)
        ids = [upload(client, auth, trade_id, f"a{i}.png") for i in range(3)]
        # Ensure initial order is as uploaded
        init_ids = list_ids(client, auth, trade_id)
        assert init_ids == ids
        # Reorder reverse
        r = client.post(f"/trades/{trade_id}/attachments/reorder", json=list(reversed(ids)), headers=auth)
        assert r.status_code == 200
        after_ids = list_ids(client, auth, trade_id)
        assert after_ids == list(reversed(ids))
        # Batch delete first two
        r2 = client.post(f"/trades/{trade_id}/attachments/batch-delete", json=after_ids[:2], headers=auth)
        assert r2.status_code == 200
        left = list_ids(client, auth, trade_id)
        assert len(left) == 1 and left[0] == after_ids[2]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

