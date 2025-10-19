from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from .db import get_db
from .deps import get_current_user
from .models import NoteTemplate
from .schemas import TemplateCreate, TemplateOut, TemplateUpdate


router = APIRouter(prefix="/templates", tags=["templates"])


def _to_out(t: NoteTemplate) -> TemplateOut:
    try:
        sections = json.loads(t.sections_json or "[]")
    except Exception:
        sections = []
    return TemplateOut(id=t.id, name=t.name, target=t.target, sections=sections, created_at=(t.created_at.isoformat() if getattr(t, 'created_at', None) else None))


@router.get("", response_model=List[TemplateOut])
def list_templates(db: Session = Depends(get_db), current = Depends(get_current_user), target: Optional[str] = Query(None)):
    q = db.query(NoteTemplate).filter(NoteTemplate.user_id == current.id)
    if target:
        q = q.filter(NoteTemplate.target == target)
    rows = q.order_by(NoteTemplate.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(body: TemplateCreate, db: Session = Depends(get_db), current = Depends(get_current_user)):
    if body.target not in ("trade", "daily"):
        raise HTTPException(400, detail="target must be 'trade' or 'daily'")
    exists = db.query(NoteTemplate).filter(NoteTemplate.user_id == current.id, NoteTemplate.name == body.name, NoteTemplate.target == body.target).first()
    if exists:
        raise HTTPException(409, detail="Template with this name already exists")
    t = NoteTemplate(user_id=current.id, name=body.name, target=body.target, sections_json=json.dumps([s.model_dump() for s in body.sections]))
    db.add(t); db.commit(); db.refresh(t)
    return _to_out(t)


@router.patch("/{tid}", response_model=TemplateOut)
def update_template(tid: int, body: TemplateUpdate, db: Session = Depends(get_db), current = Depends(get_current_user)):
    t = db.query(NoteTemplate).filter(NoteTemplate.id == tid, NoteTemplate.user_id == current.id).first()
    if not t:
        raise HTTPException(404, detail="Template not found")
    if body.name is not None:
        t.name = body.name
    if body.sections is not None:
        t.sections_json = json.dumps([s.model_dump() for s in body.sections])
    db.commit(); db.refresh(t)
    return _to_out(t)


@router.delete("/{tid}")
def delete_template(tid: int, db: Session = Depends(get_db), current = Depends(get_current_user)):
    t = db.query(NoteTemplate).filter(NoteTemplate.id == tid, NoteTemplate.user_id == current.id).first()
    if not t:
        raise HTTPException(404, detail="Template not found")
    db.delete(t); db.commit()
    return {"deleted": tid}

