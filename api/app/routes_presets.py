from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from .db import get_db
from .deps import get_current_user
from .models import MappingPreset, User
from .schemas import MappingPresetCreate, MappingPresetOut

router = APIRouter(prefix="/presets", tags=["presets"])

@router.get("", response_model=List[MappingPresetOut])
def list_presets(db: Session = Depends(get_db), current: User = Depends(get_current_user), q: str | None = None, limit: int = 50, offset: int = 0):
    query = db.query(MappingPreset).filter(MappingPreset.user_id == current.id)
    if q:
        query = query.filter(MappingPreset.name.ilike(f"%{q}%"))
    rows = query.order_by(MappingPreset.created_at.desc()).offset(offset).limit(min(limit, 100)).all()
    out = []
    for r in rows:
        out.append(MappingPresetOut(
            id=r.id,
            name=r.name,
            headers=json.loads(r.headers_json),
            mapping=json.loads(r.mapping_json),
        ))
    return out

@router.post("", response_model=MappingPresetOut, status_code=201)
def create_preset(body: MappingPresetCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    # sanity checks: required canonical fields present in mapping and refer to a header in headers
    required = {"Account","Symbol","Side","Open Time","Quantity","Entry Price"}
    hdrs = set(body.headers)
    missing = [c for c in required if c not in body.mapping]
    invalid = [k for k,v in body.mapping.items() if v not in hdrs]
    if missing:
        raise HTTPException(400, detail=f"Missing required canonical fields: {missing}")
    if invalid:
        raise HTTPException(400, detail=f"Mapping points to headers not present: {invalid}")

    exists = db.query(MappingPreset).filter(
        MappingPreset.user_id == current.id, MappingPreset.name == body.name
    ).first()
    if exists:
        raise HTTPException(409, detail="Preset name already exists")

    row = MappingPreset(
        user_id=current.id,
        name=body.name,
        headers_json=json.dumps(body.headers),
        mapping_json=json.dumps(body.mapping),
    )
    db.add(row); db.commit(); db.refresh(row)
    return MappingPresetOut(
        id=row.id, name=row.name,
        headers=json.loads(row.headers_json),
        mapping=json.loads(row.mapping_json),
    )
