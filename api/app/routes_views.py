"""
Saved Views API routes (M7 Phase 2)

Provides CRUD endpoints for managing saved filter views.
"""

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
    """
    List all saved views for current user.

    Returns views ordered by is_default desc, created_at desc.
    """
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
    """
    Create new saved view.

    Validates filters_json is valid JSON and enforces unique view names per user.
    If is_default=True, unsets any other default view for the user.
    """
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
    """
    Get saved view by ID.

    Enforces user isolation - users can only access their own views.
    """
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
    """
    Get saved view by name (case-insensitive).

    Useful for URL-friendly access like /trades?view=london-setups
    """
    view = db.query(SavedView).filter(
        SavedView.name.ilike(view_name),
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
    """
    Update saved view.

    Enforces unique view names per user and handles default view logic.
    If setting as default, unsets other default views.
    """
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
    """
    Delete saved view.

    Enforces user isolation - users can only delete their own views.
    """
    view = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.user_id == current.id
    ).first()

    if not view:
        raise HTTPException(404, detail="View not found")

    db.delete(view)
    db.commit()
    return {"message": "View deleted successfully"}
