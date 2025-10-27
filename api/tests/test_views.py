"""
Tests for Saved Views API (M7 Phase 2)
"""

from fastapi.testclient import TestClient
from app.main import app
import json
import time

client = TestClient(app)


def register_and_login():
    """Helper to create a unique user and get auth token"""
    email = f"viewtest_{int(time.time() * 1000000)}@example.com"
    pwd = "TestPwd123!"
    client.post("/auth/register", json={"email": email, "password": pwd})
    r = client.post("/auth/login", data={"username": email, "password": pwd})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_saved_view():
    """Test creating a saved view"""
    auth = register_and_login()

    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "contains", "value": "EUR"}
        ]
    }

    payload = {
        "name": "EUR Trades",
        "description": "All EUR pairs",
        "filters_json": json.dumps(filter_dsl),
        "is_default": False
    }

    r = client.post("/views", json=payload, headers=auth)
    assert r.status_code == 201, r.text
    view = r.json()
    assert view["name"] == "EUR Trades"
    assert view["description"] == "All EUR pairs"
    assert view["is_default"] == False
    assert "id" in view
    assert "created_at" in view


def test_list_saved_views():
    """Test listing saved views"""
    auth = register_and_login()

    # Create two views
    for i in range(2):
        payload = {
            "name": f"View {i}",
            "filters_json": json.dumps({"operator": "AND", "conditions": []})
        }
        client.post("/views", json=payload, headers=auth)

    # List views
    r = client.get("/views", headers=auth)
    assert r.status_code == 200
    views = r.json()
    assert len(views) == 2


def test_list_views_ordering():
    """Test that views are ordered by is_default desc, created_at desc"""
    auth = register_and_login()

    # Create three views, set second as default
    client.post("/views", json={
        "name": "First",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": False
    }, headers=auth)

    time.sleep(0.1)  # Ensure different created_at

    client.post("/views", json={
        "name": "Second (Default)",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": True
    }, headers=auth)

    time.sleep(0.1)

    client.post("/views", json={
        "name": "Third",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": False
    }, headers=auth)

    # List views
    r = client.get("/views", headers=auth)
    views = r.json()
    assert views[0]["name"] == "Second (Default)"
    assert views[0]["is_default"] == True
    # Next two should be ordered by created_at desc
    assert views[1]["name"] == "Third"
    assert views[2]["name"] == "First"


def test_get_saved_view_by_id():
    """Test retrieving view by ID"""
    auth = register_and_login()

    # Create view
    payload = {
        "name": "Test View",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    r = client.post("/views", json=payload, headers=auth)
    view_id = r.json()["id"]

    # Get by ID
    r = client.get(f"/views/{view_id}", headers=auth)
    assert r.status_code == 200
    view = r.json()
    assert view["name"] == "Test View"
    assert view["id"] == view_id


def test_get_saved_view_by_name():
    """Test retrieving view by name (case-insensitive)"""
    auth = register_and_login()

    # Create view
    payload = {
        "name": "London Trades",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    client.post("/views", json=payload, headers=auth)

    # Get by name (exact case)
    r = client.get("/views/by-name/London Trades", headers=auth)
    assert r.status_code == 200
    view = r.json()
    assert view["name"] == "London Trades"

    # Get by name (different case)
    r = client.get("/views/by-name/london trades", headers=auth)
    assert r.status_code == 200
    view = r.json()
    assert view["name"] == "London Trades"


def test_update_saved_view():
    """Test updating a saved view"""
    auth = register_and_login()

    # Create view
    payload = {
        "name": "Original Name",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    r = client.post("/views", json=payload, headers=auth)
    view_id = r.json()["id"]

    # Update view
    update = {"name": "Updated Name", "description": "New description"}
    r = client.patch(f"/views/{view_id}", json=update, headers=auth)
    assert r.status_code == 200
    view = r.json()
    assert view["name"] == "Updated Name"
    assert view["description"] == "New description"


def test_delete_saved_view():
    """Test deleting a saved view"""
    auth = register_and_login()

    # Create view
    payload = {
        "name": "To Delete",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    r = client.post("/views", json=payload, headers=auth)
    view_id = r.json()["id"]

    # Delete view
    r = client.delete(f"/views/{view_id}", headers=auth)
    assert r.status_code == 200

    # Verify deleted
    r = client.get(f"/views/{view_id}", headers=auth)
    assert r.status_code == 404


def test_set_default_view():
    """Test setting a view as default (only one default allowed)"""
    auth = register_and_login()

    # Create first view as default
    r1 = client.post("/views", json={
        "name": "View 1",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": True
    }, headers=auth)
    assert r1.status_code == 201

    # Create second view as default (should unset first)
    r2 = client.post("/views", json={
        "name": "View 2",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": True
    }, headers=auth)
    assert r2.status_code == 201

    # Check that only View 2 is default
    r = client.get("/views", headers=auth)
    views = r.json()
    defaults = [v for v in views if v["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "View 2"


def test_update_to_default_unsets_others():
    """Test that updating a view to default unsets other defaults"""
    auth = register_and_login()

    # Create two views
    r1 = client.post("/views", json={
        "name": "View 1",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": True
    }, headers=auth)
    view1_id = r1.json()["id"]

    r2 = client.post("/views", json={
        "name": "View 2",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": False
    }, headers=auth)
    view2_id = r2.json()["id"]

    # Update View 2 to be default
    r = client.patch(f"/views/{view2_id}", json={"is_default": True}, headers=auth)
    assert r.status_code == 200

    # Check that only View 2 is default
    r = client.get("/views", headers=auth)
    views = r.json()
    defaults = [v for v in views if v["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == view2_id


def test_duplicate_name_rejected():
    """Test that duplicate view names are rejected"""
    auth = register_and_login()

    # Create first view
    payload = {
        "name": "Duplicate",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    r = client.post("/views", json=payload, headers=auth)
    assert r.status_code == 201

    # Try to create second with same name
    r = client.post("/views", json=payload, headers=auth)
    assert r.status_code == 400
    assert "already exists" in r.text.lower()


def test_update_duplicate_name_rejected():
    """Test that updating to a duplicate name is rejected"""
    auth = register_and_login()

    # Create two views
    client.post("/views", json={
        "name": "View 1",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }, headers=auth)

    r2 = client.post("/views", json={
        "name": "View 2",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }, headers=auth)
    view2_id = r2.json()["id"]

    # Try to rename View 2 to View 1
    r = client.patch(f"/views/{view2_id}", json={"name": "View 1"}, headers=auth)
    assert r.status_code == 400
    assert "already exists" in r.text.lower()


def test_invalid_json_rejected():
    """Test that invalid filters_json is rejected"""
    auth = register_and_login()

    payload = {
        "name": "Bad JSON",
        "filters_json": "this is not json"
    }

    r = client.post("/views", json=payload, headers=auth)
    assert r.status_code == 400
    assert "invalid" in r.text.lower()


def test_user_isolation():
    """Test that users can only access their own views"""
    auth1 = register_and_login()
    auth2 = register_and_login()

    # User 1 creates a view
    r = client.post("/views", json={
        "name": "User 1 View",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }, headers=auth1)
    view_id = r.json()["id"]

    # User 2 tries to access User 1's view
    r = client.get(f"/views/{view_id}", headers=auth2)
    assert r.status_code == 404

    # User 2 tries to update User 1's view
    r = client.patch(f"/views/{view_id}", json={"name": "Hacked"}, headers=auth2)
    assert r.status_code == 404

    # User 2 tries to delete User 1's view
    r = client.delete(f"/views/{view_id}", headers=auth2)
    assert r.status_code == 404


def test_apply_saved_view_to_trades_by_id():
    """Test using saved view in trades endpoint by ID"""
    auth = register_and_login()

    # Create view with filter
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "contains", "value": "EUR"}
        ]
    }
    payload = {
        "name": "EUR Only",
        "filters_json": json.dumps(filter_dsl)
    }
    r = client.post("/views", json=payload, headers=auth)
    view_id = r.json()["id"]

    # Apply view to trades query (no trades, but should not error)
    r = client.get(f"/trades?view={view_id}", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_apply_saved_view_to_trades_by_name():
    """Test using saved view in trades endpoint by name"""
    auth = register_and_login()

    # Create view with filter
    filter_dsl = {
        "operator": "AND",
        "conditions": [
            {"field": "symbol", "op": "contains", "value": "GBP"}
        ]
    }
    payload = {
        "name": "GBP Only",
        "filters_json": json.dumps(filter_dsl)
    }
    client.post("/views", json=payload, headers=auth)

    # Apply view to trades query by name
    r = client.get("/trades?view=GBP Only", headers=auth)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_apply_nonexistent_view_returns_404():
    """Test that applying non-existent view returns 404"""
    auth = register_and_login()

    # Try to apply view by ID that doesn't exist
    r = client.get("/trades?view=99999", headers=auth)
    assert r.status_code == 404

    # Try to apply view by name that doesn't exist
    r = client.get("/trades?view=Nonexistent", headers=auth)
    assert r.status_code == 404


def test_view_not_found_by_id():
    """Test that getting non-existent view by ID returns 404"""
    auth = register_and_login()

    r = client.get("/views/99999", headers=auth)
    assert r.status_code == 404


def test_view_not_found_by_name():
    """Test that getting non-existent view by name returns 404"""
    auth = register_and_login()

    r = client.get("/views/by-name/Nonexistent", headers=auth)
    assert r.status_code == 404


def test_update_nonexistent_view():
    """Test that updating non-existent view returns 404"""
    auth = register_and_login()

    r = client.patch("/views/99999", json={"name": "New Name"}, headers=auth)
    assert r.status_code == 404


def test_delete_nonexistent_view():
    """Test that deleting non-existent view returns 404"""
    auth = register_and_login()

    r = client.delete("/views/99999", headers=auth)
    assert r.status_code == 404


def test_empty_name_rejected():
    """Test that empty name is rejected"""
    auth = register_and_login()

    payload = {
        "name": "",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }

    r = client.post("/views", json=payload, headers=auth)
    assert r.status_code == 422  # Pydantic validation error


def test_update_filters():
    """Test updating filters of a saved view"""
    auth = register_and_login()

    # Create view
    original_filters = {"operator": "AND", "conditions": [{"field": "symbol", "op": "eq", "value": "EURUSD"}]}
    r = client.post("/views", json={
        "name": "Test",
        "filters_json": json.dumps(original_filters)
    }, headers=auth)
    view_id = r.json()["id"]

    # Update filters
    new_filters = {"operator": "OR", "conditions": [{"field": "symbol", "op": "contains", "value": "GBP"}]}
    r = client.patch(f"/views/{view_id}", json={
        "filters_json": json.dumps(new_filters)
    }, headers=auth)
    assert r.status_code == 200
    view = r.json()
    assert json.loads(view["filters_json"]) == new_filters
