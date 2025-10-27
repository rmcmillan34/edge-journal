# M7 Phase 2: Saved Views - Implementation Plan

**Status**: Planning
**Version**: 0.7.2
**Last Updated**: 2025-10-25

## Overview

Phase 2 adds the ability to save, name, and recall filter combinations. Users can:
- Save current filter as a named view
- Quickly switch between saved views
- Set a default view that loads automatically
- Share views via URL-friendly names
- Manage views (rename, update, delete)

---

## Goals

1. **Persist filter combinations** with meaningful names
2. **Quick access** to common filter patterns
3. **URL addressability** via view name or ID
4. **Default view** support for instant filtering on page load
5. **Manage views** in Settings page

---

## Database Schema

### Migration: `0018_saved_views`

**Location**: `/api/alembic/versions/0018_saved_views.py`

```sql
CREATE TABLE saved_views (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,

    -- Filter configuration (Phase 1)
    filters_json TEXT NOT NULL,        -- Filter DSL JSON

    -- Display configuration (Future phases)
    columns_json TEXT,                 -- Column visibility/order (optional)
    sort_json TEXT,                    -- Sort configuration (optional)
    group_by VARCHAR(64),              -- Optional grouping field (optional)

    -- Metadata
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_view_name UNIQUE(user_id, name)
);

CREATE INDEX idx_saved_views_user ON saved_views(user_id);
CREATE INDEX idx_saved_views_default ON saved_views(user_id, is_default);
```

**Key Design Decisions**:
- `filters_json`: Stores complete FilterDSL object as JSON string
- `columns_json`, `sort_json`, `group_by`: Placeholders for future enhancements (Phase 3+)
- `is_default`: Only one view per user can be default (enforce in API)
- `unique_user_view_name`: Prevents duplicate view names per user
- Cascade delete: Views are deleted when user is deleted

**Example Row**:
```json
{
  "id": 1,
  "user_id": 42,
  "name": "London A-Setups",
  "description": "Winning A-grade setups during London session",
  "filters_json": "{\"operator\":\"AND\",\"conditions\":[{\"field\":\"playbook.grade\",\"op\":\"eq\",\"value\":\"A\"},{\"field\":\"net_pnl\",\"op\":\"gt\",\"value\":0}]}",
  "columns_json": null,
  "sort_json": null,
  "group_by": null,
  "is_default": false,
  "created_at": "2025-10-25T10:30:00Z",
  "updated_at": "2025-10-25T10:30:00Z"
}
```

---

## Backend Implementation

### Task 1: Database Migration

**File**: `/api/alembic/versions/0018_saved_views.py`

**Action**: Create Alembic migration script

```python
"""M7 Phase 2: Saved Views

Revision ID: 0018_saved_views
Revises: 0017_m6_account_closure
Create Date: 2025-10-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0018_saved_views'
down_revision = '0017_m6_account_closure'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'saved_views',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filters_json', sa.Text(), nullable=False),
        sa.Column('columns_json', sa.Text(), nullable=True),
        sa.Column('sort_json', sa.Text(), nullable=True),
        sa.Column('group_by', sa.String(length=64), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'name', name='unique_user_view_name')
    )
    op.create_index('idx_saved_views_user', 'saved_views', ['user_id'])
    op.create_index('idx_saved_views_default', 'saved_views', ['user_id', 'is_default'])

def downgrade():
    op.drop_index('idx_saved_views_default')
    op.drop_index('idx_saved_views_user')
    op.drop_table('saved_views')
```

### Task 2: SQLAlchemy Model

**File**: `/api/app/models.py`

Add `SavedView` model:

```python
class SavedView(Base):
    __tablename__ = "saved_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # Configuration (JSON strings)
    filters_json = Column(Text, nullable=False)
    columns_json = Column(Text, nullable=True)
    sort_json = Column(Text, nullable=True)
    group_by = Column(String(64), nullable=True)

    # Metadata
    is_default = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="saved_views")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_user_view_name'),
        Index('idx_saved_views_default', 'user_id', 'is_default'),
    )
```

**Also update User model**:
```python
class User(Base):
    # ... existing fields ...
    saved_views = relationship("SavedView", back_populates="user", cascade="all, delete-orphan")
```

### Task 3: Pydantic Schemas

**File**: `/api/app/schemas.py`

Add SavedView schemas:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class SavedViewCreate(BaseModel):
    """Schema for creating a saved view"""
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    filters_json: str = Field(..., description="Filter DSL as JSON string")
    columns_json: Optional[str] = None
    sort_json: Optional[str] = None
    group_by: Optional[str] = None
    is_default: bool = False

class SavedViewUpdate(BaseModel):
    """Schema for updating a saved view"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    filters_json: Optional[str] = None
    columns_json: Optional[str] = None
    sort_json: Optional[str] = None
    group_by: Optional[str] = None
    is_default: Optional[bool] = None

class SavedViewOut(BaseModel):
    """Schema for saved view response"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    filters_json: str
    columns_json: Optional[str]
    sort_json: Optional[str]
    group_by: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Task 4: API Endpoints

**File**: `/api/app/routes_views.py` (NEW)

Create new router for saved views:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from .db import get_db
from .deps import get_current_user
from .models import SavedView, User
from .schemas import SavedViewCreate, SavedViewUpdate, SavedViewOut

router = APIRouter(prefix="/views", tags=["views"])


@router.get("", response_model=List[SavedViewOut])
def list_saved_views(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """List all saved views for current user"""
    views = db.query(SavedView).filter(SavedView.user_id == current.id).order_by(
        SavedView.is_default.desc(),
        SavedView.created_at.desc()
    ).all()
    return views


@router.post("", status_code=201, response_model=SavedViewOut)
def create_saved_view(
    body: SavedViewCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Create new saved view"""

    # Validate filters_json is valid JSON
    try:
        json.loads(body.filters_json)
    except json.JSONDecodeError:
        raise HTTPException(400, detail="Invalid filters_json: must be valid JSON")

    # Check if name already exists for this user
    existing = db.query(SavedView).filter(
        SavedView.user_id == current.id,
        SavedView.name == body.name
    ).first()
    if existing:
        raise HTTPException(400, detail=f"View with name '{body.name}' already exists")

    # If setting as default, unset other defaults
    if body.is_default:
        db.query(SavedView).filter(
            SavedView.user_id == current.id,
            SavedView.is_default == True
        ).update({"is_default": False})

    view = SavedView(
        user_id=current.id,
        name=body.name,
        description=body.description,
        filters_json=body.filters_json,
        columns_json=body.columns_json,
        sort_json=body.sort_json,
        group_by=body.group_by,
        is_default=body.is_default
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


@router.get("/{view_id}", response_model=SavedViewOut)
def get_saved_view(
    view_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Get saved view by ID"""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current.id
    ).first()

    if not view:
        raise HTTPException(404, detail="View not found")

    return view


@router.get("/by-name/{view_name}", response_model=SavedViewOut)
def get_saved_view_by_name(
    view_name: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Get saved view by name (for URL-friendly access)"""
    view = db.query(SavedView).filter(
        SavedView.name.ilike(view_name),  # Case-insensitive
        SavedView.user_id == current.id
    ).first()

    if not view:
        raise HTTPException(404, detail=f"View '{view_name}' not found")

    return view


@router.patch("/{view_id}", response_model=SavedViewOut)
def update_saved_view(
    view_id: int,
    body: SavedViewUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Update saved view"""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current.id
    ).first()

    if not view:
        raise HTTPException(404, detail="View not found")

    # Check name uniqueness if changing name
    if body.name and body.name != view.name:
        existing = db.query(SavedView).filter(
            SavedView.user_id == current.id,
            SavedView.name == body.name
        ).first()
        if existing:
            raise HTTPException(400, detail=f"View with name '{body.name}' already exists")

    # If setting as default, unset other defaults
    if body.is_default and not view.is_default:
        db.query(SavedView).filter(
            SavedView.user_id == current.id,
            SavedView.is_default == True,
            SavedView.id != view_id
        ).update({"is_default": False})

    # Update fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(view, field, value)

    db.commit()
    db.refresh(view)
    return view


@router.delete("/{view_id}")
def delete_saved_view(
    view_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """Delete saved view"""
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current.id
    ).first()

    if not view:
        raise HTTPException(404, detail="View not found")

    db.delete(view)
    db.commit()
    return {"message": "View deleted successfully"}
```

**Update main.py** to include router:
```python
from .routes_views import router as views_router

app.include_router(views_router)
```

### Task 5: Update Trades Endpoint

**File**: `/api/app/routes_trades.py`

Modify `list_trades` to support `view` parameter:

```python
@router.get("", response_model=List[TradeOut])
def list_trades(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    symbol: Optional[str] = None,
    account: Optional[str] = None,
    start: Optional[str] = Query(None, description="YYYY-MM-DD inclusive"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD inclusive"),
    sort: Optional[str] = Query(None, description="Sort by field"),
    filters: Optional[str] = Query(None, description="Filter DSL JSON string"),
    view: Optional[str] = Query(None, description="Saved view ID or name"),
):
    # ... existing query setup ...

    # Priority: view > filters > legacy params
    if view:
        # Try to load view by ID first, then by name
        from .models import SavedView
        saved_view = None

        # Try as integer ID
        try:
            view_id = int(view)
            saved_view = db.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.user_id == current.id
            ).first()
        except ValueError:
            pass

        # Try by name if not found
        if not saved_view:
            saved_view = db.query(SavedView).filter(
                SavedView.name.ilike(view),
                SavedView.user_id == current.id
            ).first()

        if not saved_view:
            raise HTTPException(404, detail=f"View '{view}' not found")

        # Apply saved view filters
        try:
            from .filters import FilterCompiler
            filter_dsl = json.loads(saved_view.filters_json)
            compiler = FilterCompiler(user_id=current.id)
            q = compiler.compile(filter_dsl, q)
        except Exception as e:
            raise HTTPException(400, detail=f"Failed to apply view filters: {str(e)}")

    elif filters:
        # ... existing filters logic ...

    elif symbol or account or start or end:
        # ... existing legacy params logic ...

    # ... rest of endpoint ...
```

### Task 6: Testing

**File**: `/api/tests/test_views.py` (NEW)

Create comprehensive test suite:

```python
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def register_and_login():
    email = f"viewtest_{hash(str(__file__))}@example.com"
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


def test_get_saved_view_by_name():
    """Test retrieving view by name"""
    auth = register_and_login()

    # Create view
    payload = {
        "name": "London Trades",
        "filters_json": json.dumps({"operator": "AND", "conditions": []})
    }
    client.post("/views", json=payload, headers=auth)

    # Get by name
    r = client.get("/views/by-name/London Trades", headers=auth)
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
    """Test setting a view as default"""
    auth = register_and_login()

    # Create two views
    r1 = client.post("/views", json={
        "name": "View 1",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": True
    }, headers=auth)

    r2 = client.post("/views", json={
        "name": "View 2",
        "filters_json": json.dumps({"operator": "AND", "conditions": []}),
        "is_default": True  # Should unset View 1
    }, headers=auth)

    # Check that only View 2 is default
    r = client.get("/views", headers=auth)
    views = r.json()
    defaults = [v for v in views if v["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "View 2"


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


def test_apply_saved_view_to_trades():
    """Test using saved view in trades endpoint"""
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

    # Apply view to trades query
    r = client.get(f"/trades?view={view_id}", headers=auth)
    assert r.status_code == 200

    # Also test by name
    r = client.get("/trades?view=EUR Only", headers=auth)
    assert r.status_code == 200
```

---

## Frontend Implementation

### Task 7: TypeScript Types

**File**: `/web/app/components/filters/types.ts`

Add SavedView types:

```typescript
export interface SavedView {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  filters_json: string;
  columns_json?: string;
  sort_json?: string;
  group_by?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface SavedViewCreate {
  name: string;
  description?: string;
  filters_json: string;
  is_default?: boolean;
}
```

### Task 8: Save View Modal

**File**: `/web/app/components/filters/SaveViewModal.tsx` (NEW)

Create modal for saving current filters:

```tsx
"use client";

import { useState } from "react";
import { FilterDSL } from "./types";

interface SaveViewModalProps {
  filters: FilterDSL;
  onSave: (name: string, description: string, isDefault: boolean) => void;
  onClose: () => void;
}

export default function SaveViewModal({ filters, onSave, onClose }: SaveViewModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [error, setError] = useState("");

  const handleSave = () => {
    if (!name.trim()) {
      setError("View name is required");
      return;
    }

    onSave(name.trim(), description.trim(), isDefault);
  };

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(0,0,0,0.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000
    }}>
      <div style={{
        background: "var(--ctp-base)",
        borderRadius: "8px",
        padding: "24px",
        maxWidth: "500px",
        width: "90%",
        boxShadow: "0 4px 12px rgba(0,0,0,0.3)"
      }}>
        <h2 style={{ marginTop: 0 }}>Save Filter View</h2>

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}>
            View Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., EUR Winning Trades"
            style={{
              width: "100%",
              padding: "8px 12px",
              borderRadius: "4px",
              border: "1px solid var(--ctp-surface2)"
            }}
          />
        </div>

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}>
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of this view..."
            rows={3}
            style={{
              width: "100%",
              padding: "8px 12px",
              borderRadius: "4px",
              border: "1px solid var(--ctp-surface2)",
              resize: "vertical"
            }}
          />
        </div>

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
            />
            <span>Set as default view (loads automatically)</span>
          </label>
        </div>

        {error && (
          <div style={{
            padding: "8px 12px",
            background: "var(--ctp-red)",
            color: "var(--ctp-crust)",
            borderRadius: "4px",
            marginBottom: "16px"
          }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              padding: "8px 16px",
              borderRadius: "4px",
              background: "var(--ctp-surface1)",
              border: "1px solid var(--ctp-surface2)",
              cursor: "pointer"
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            style={{
              padding: "8px 16px",
              borderRadius: "4px",
              background: "var(--ctp-green)",
              color: "var(--ctp-crust)",
              border: "none",
              cursor: "pointer",
              fontWeight: 600
            }}
          >
            Save View
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Task 9: View Selector Dropdown

**File**: `/web/app/components/filters/ViewSelector.tsx` (NEW)

Dropdown to quick-switch between views:

```tsx
"use client";

import { useState, useEffect } from "react";
import { SavedView } from "./types";

interface ViewSelectorProps {
  currentViewId?: number;
  onSelectView: (view: SavedView | null) => void;
  onManageViews: () => void;
}

export default function ViewSelector({ currentViewId, onSelectView, onManageViews }: ViewSelectorProps) {
  const [views, setViews] = useState<SavedView[]>([]);
  const [loading, setLoading] = useState(false);
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  useEffect(() => {
    loadViews();
  }, []);

  const loadViews = async () => {
    const token = localStorage.getItem("ej_token");
    if (!token) return;

    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/views`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (r.ok) {
        const data = await r.json();
        setViews(data);
      }
    } catch (e) {
      console.error("Failed to load views:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === "") {
      onSelectView(null);
    } else {
      const view = views.find((v) => v.id === parseInt(value));
      if (view) onSelectView(view);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <label style={{ fontWeight: 600, fontSize: "14px" }}>Saved View:</label>
      <select
        value={currentViewId || ""}
        onChange={handleChange}
        disabled={loading}
        style={{
          padding: "6px 12px",
          borderRadius: "4px",
          border: "1px solid var(--ctp-surface2)",
          minWidth: "200px"
        }}
      >
        <option value="">No view (show all)</option>
        {views.map((view) => (
          <option key={view.id} value={view.id}>
            {view.name} {view.is_default ? "⭐" : ""}
          </option>
        ))}
      </select>
      <button
        onClick={onManageViews}
        style={{
          padding: "6px 12px",
          borderRadius: "4px",
          background: "var(--ctp-surface1)",
          border: "1px solid var(--ctp-surface2)",
          cursor: "pointer",
          fontSize: "14px"
        }}
      >
        Manage
      </button>
    </div>
  );
}
```

### Task 10: View Management Page

**File**: `/web/app/settings/views/page.tsx` (NEW)

Full CRUD interface for managing saved views:

```tsx
"use client";

import { useState, useEffect } from "react";
import { SavedView } from "../../components/filters/types";

export default function SavedViewsSettingsPage() {
  const [views, setViews] = useState<SavedView[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  useEffect(() => {
    loadViews();
  }, []);

  const loadViews = async () => {
    const token = localStorage.getItem("ej_token");
    if (!token) return;

    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/views`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (r.ok) {
        const data = await r.json();
        setViews(data);
      } else {
        setError("Failed to load views");
      }
    } catch (e) {
      setError("Failed to load views");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (viewId: number) => {
    if (!confirm("Delete this view? This cannot be undone.")) return;

    const token = localStorage.getItem("ej_token");
    if (!token) return;

    try {
      const r = await fetch(`${API_BASE}/views/${viewId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (r.ok) {
        loadViews();
      } else {
        setError("Failed to delete view");
      }
    } catch (e) {
      setError("Failed to delete view");
    }
  };

  const handleSetDefault = async (viewId: number) => {
    const token = localStorage.getItem("ej_token");
    if (!token) return;

    try {
      const r = await fetch(`${API_BASE}/views/${viewId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ is_default: true })
      });
      if (r.ok) {
        loadViews();
      } else {
        setError("Failed to set default view");
      }
    } catch (e) {
      setError("Failed to set default view");
    }
  };

  return (
    <main style={{ maxWidth: 800, margin: "2rem auto", fontFamily: "system-ui,sans-serif" }}>
      <h1>Manage Saved Views</h1>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : views.length === 0 ? (
        <p>No saved views yet. Create one from the Trades page!</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid var(--ctp-surface2)" }}>
              <th style={{ textAlign: "left", padding: "12px" }}>Name</th>
              <th style={{ textAlign: "left", padding: "12px" }}>Description</th>
              <th style={{ textAlign: "center", padding: "12px" }}>Default</th>
              <th style={{ textAlign: "center", padding: "12px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {views.map((view) => (
              <tr key={view.id} style={{ borderBottom: "1px solid var(--ctp-surface1)" }}>
                <td style={{ padding: "12px", fontWeight: 600 }}>{view.name}</td>
                <td style={{ padding: "12px", color: "var(--ctp-overlay1)" }}>
                  {view.description || "-"}
                </td>
                <td style={{ padding: "12px", textAlign: "center" }}>
                  {view.is_default ? "⭐" : "-"}
                </td>
                <td style={{ padding: "12px", textAlign: "center" }}>
                  <button
                    onClick={() => handleSetDefault(view.id)}
                    disabled={view.is_default}
                    style={{
                      padding: "4px 8px",
                      marginRight: "8px",
                      fontSize: "12px",
                      cursor: view.is_default ? "not-allowed" : "pointer"
                    }}
                  >
                    Set Default
                  </button>
                  <button
                    onClick={() => handleDelete(view.id)}
                    style={{
                      padding: "4px 8px",
                      fontSize: "12px",
                      background: "var(--ctp-red)",
                      color: "var(--ctp-crust)",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer"
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ marginTop: "24px" }}>
        <a href="/trades" style={{ color: "var(--ctp-blue)" }}>
          ← Back to Trades
        </a>
      </div>
    </main>
  );
}
```

### Task 11: Integrate with Trades Page

**File**: `/web/app/trades/page.tsx`

Update trades page to support saved views:

1. Add ViewSelector component
2. Add "Save View" button
3. Handle loading default view on mount
4. Apply selected view filters

```tsx
// Add imports
import SaveViewModal from "../components/filters/SaveViewModal";
import ViewSelector from "../components/filters/ViewSelector";
import { SavedView } from "../components/filters/types";

// Add state
const [showSaveModal, setShowSaveModal] = useState(false);
const [currentView, setCurrentView] = useState<SavedView | null>(null);

// Load default view on mount
useEffect(() => {
  if (!token) return;

  // Check for view in URL
  const viewParam = searchParams?.get('view');
  if (viewParam) {
    loadViewByNameOrId(viewParam);
  } else {
    // Load default view
    loadDefaultView();
  }
}, [token, searchParams]);

// ... add helper functions ...

// Add UI in render:
{token && (
  <div style={{ marginBottom: "16px" }}>
    <ViewSelector
      currentViewId={currentView?.id}
      onSelectView={handleSelectView}
      onManageViews={() => router.push("/settings/views")}
    />
  </div>
)}

{/* After FilterBuilder */}
{token && activeFilters && (
  <button
    onClick={() => setShowSaveModal(true)}
    style={{
      padding: "8px 16px",
      marginBottom: "16px",
      background: "var(--ctp-blue)",
      color: "var(--ctp-crust)",
      border: "none",
      borderRadius: "4px",
      cursor: "pointer"
    }}
  >
    💾 Save as View
  </button>
)}

{/* Save Modal */}
{showSaveModal && activeFilters && (
  <SaveViewModal
    filters={activeFilters}
    onSave={handleSaveView}
    onClose={() => setShowSaveModal(false)}
  />
)}
```

---

## Implementation Timeline

### Week 1: Backend Foundation
- Day 1-2: Migration + Models + Schemas
- Day 2-3: API endpoints + routes
- Day 4: Testing

### Week 2: Frontend Integration
- Day 1: TypeScript types + SaveViewModal
- Day 2: ViewSelector component
- Day 3: View management page
- Day 4: Trades page integration
- Day 5: End-to-end testing + polish

**Total Estimate**: 1.5-2 weeks

---

## Testing Checklist

### Backend Tests
- [ ] Create saved view
- [ ] List saved views (ordered by default, then created_at)
- [ ] Get view by ID
- [ ] Get view by name (case-insensitive)
- [ ] Update view (name, description, filters)
- [ ] Delete view
- [ ] Set default view (unsets others)
- [ ] Duplicate name validation
- [ ] Apply view to trades query (by ID)
- [ ] Apply view to trades query (by name)
- [ ] User isolation (can't access other user's views)

### Frontend Tests
- [ ] Save current filters as view
- [ ] Load view from dropdown
- [ ] Load default view on page load
- [ ] URL param ?view=<name> loads view
- [ ] Manage views page (list, delete, set default)
- [ ] Save modal validation
- [ ] View selector shows star for default
- [ ] Clear view selection

---

## Success Metrics

- [ ] Users can save filter combinations with meaningful names
- [ ] Views load in <500ms
- [ ] Default view loads automatically on page visit
- [ ] URL sharing works (/trades?view=london-a-setups)
- [ ] View management is intuitive (Settings page)
- [ ] No duplicate names allowed per user
- [ ] Only one default view per user

---

## Future Enhancements (Phase 3+)

- Export/import view configurations
- Share views between users (team views)
- View templates (system-provided common patterns)
- Track view usage analytics
- Schedule reports based on saved views (Phase 3)
