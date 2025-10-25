from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from .db import get_db
from .deps import get_current_user
from .models import User, BreachEvent
from .schemas import BreachEventOut

router = APIRouter(prefix="/breaches", tags=["breaches"])


@router.get("", response_model=List[BreachEventOut])
def list_breaches(
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD inclusive for day/week/month scopes; for trade scope, compares date string"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD inclusive"),
    scope: Optional[str] = Query(None, description="Filter by scope: day|week|month|trade"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(BreachEvent).filter(BreachEvent.user_id == current.id)
    if scope:
        q = q.filter(BreachEvent.scope == scope)
    if acknowledged is not None:
        q = q.filter(BreachEvent.acknowledged == acknowledged)
    # naive string compare for date_or_week that is YYYY-MM-DD or YYYY-Wnn
    if start:
        q = q.filter(BreachEvent.date_or_week >= start)
    if end:
        q = q.filter(BreachEvent.date_or_week <= end)
    rows = q.order_by(BreachEvent.created_at.desc()).all()
    out: List[BreachEventOut] = []
    for r in rows:
        try:
            details = json.loads(r.details_json) if r.details_json else None
        except Exception:
            details = None
        out.append(BreachEventOut(
            id=r.id,
            scope=r.scope,
            date_or_week=r.date_or_week,
            rule_key=r.rule_key,
            details=details,
            acknowledged=r.acknowledged,
            created_at=r.created_at.isoformat() if r.created_at else None,
        ))
    return out


@router.post("/{breach_id}/ack")
def acknowledge_breach(
    breach_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.query(BreachEvent).filter(BreachEvent.id == breach_id, BreachEvent.user_id == current.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Breach not found")
    row.acknowledged = True
    row.acknowledged_at = datetime.utcnow()
    row.acknowledged_by = current.id
    db.commit()
    return {"ok": True}

