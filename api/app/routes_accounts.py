from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from .db import get_db
from .deps import get_current_user
from .models import Account, User
from .schemas import AccountCreate, AccountOut, AccountUpdate, AccountClose, AccountReopen

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("")
def list_accounts(
    include_closed: bool = False,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """List accounts, optionally including closed accounts (M6)"""
    query = db.query(Account).filter(Account.user_id == current.id)
    if not include_closed:
        query = query.filter(Account.status == "active")
    rows = query.order_by(Account.name.asc()).all()

    # Manually serialize to handle datetime fields
    return [
        {
            "id": row.id,
            "name": row.name,
            "broker_label": row.broker_label,
            "base_ccy": row.base_ccy,
            "status": row.status,
            "account_max_risk_pct": row.account_max_risk_pct,
            "closed_at": row.closed_at.isoformat() if row.closed_at else None,
            "close_reason": row.close_reason,
            "close_note": row.close_note,
        }
        for row in rows
    ]

@router.post("", status_code=201)
def create_account(body: AccountCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    exists = db.query(Account).filter(Account.user_id == current.id, Account.name == body.name).first()
    if exists:
        raise HTTPException(409, detail="Account name already exists")
    row = Account(user_id=current.id, name=body.name, broker_label=body.broker_label, base_ccy=body.base_ccy, status="active")
    db.add(row); db.commit(); db.refresh(row)

    return {
        "id": row.id,
        "name": row.name,
        "broker_label": row.broker_label,
        "base_ccy": row.base_ccy,
        "status": row.status,
        "account_max_risk_pct": row.account_max_risk_pct,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "close_reason": row.close_reason,
        "close_note": row.close_note,
    }


@router.patch("/{account_id}")
def update_account(account_id: int, body: AccountUpdate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    row = db.query(Account).filter(Account.id == account_id, Account.user_id == current.id).first()
    if not row:
        raise HTTPException(404, detail="Account not found")
    if body.name is not None:
        # prevent duplicate names for this user
        exists = db.query(Account).filter(Account.user_id == current.id, Account.name == body.name, Account.id != account_id).first()
        if exists:
            raise HTTPException(409, detail="Account name already exists")
        row.name = body.name
    if body.broker_label is not None:
        row.broker_label = body.broker_label
    if body.base_ccy is not None:
        row.base_ccy = body.base_ccy
    if body.status is not None:
        row.status = body.status
    if body.account_max_risk_pct is not None:
        row.account_max_risk_pct = body.account_max_risk_pct
    db.commit(); db.refresh(row)

    return {
        "id": row.id,
        "name": row.name,
        "broker_label": row.broker_label,
        "base_ccy": row.base_ccy,
        "status": row.status,
        "account_max_risk_pct": row.account_max_risk_pct,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "close_reason": row.close_reason,
        "close_note": row.close_note,
    }


@router.post("/{account_id}/close")
def close_account(account_id: int, body: AccountClose, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Close an account with reason and optional note (M6 account lifecycle)"""
    row = db.query(Account).filter(Account.id == account_id, Account.user_id == current.id).first()
    if not row:
        raise HTTPException(404, detail="Account not found")
    if row.status == "closed":
        raise HTTPException(400, detail="Account is already closed")

    row.status = "closed"
    row.closed_at = datetime.now(timezone.utc)
    row.close_reason = body.reason
    row.close_note = body.note
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "name": row.name,
        "broker_label": row.broker_label,
        "base_ccy": row.base_ccy,
        "status": row.status,
        "account_max_risk_pct": row.account_max_risk_pct,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "close_reason": row.close_reason,
        "close_note": row.close_note,
    }


@router.post("/{account_id}/reopen")
def reopen_account(account_id: int, body: AccountReopen, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Reopen a closed account (M6 account lifecycle)"""
    row = db.query(Account).filter(Account.id == account_id, Account.user_id == current.id).first()
    if not row:
        raise HTTPException(404, detail="Account not found")
    if row.status != "closed":
        raise HTTPException(400, detail="Account is not closed")

    # Audit note: append reopen note to close_note if provided
    if body.note:
        reopen_timestamp = datetime.now(timezone.utc).isoformat()
        reopen_audit = f"\n[Reopened {reopen_timestamp}] {body.note}"
        row.close_note = (row.close_note or "") + reopen_audit

    row.status = "active"
    # Keep closed_at and close_reason for audit trail
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "name": row.name,
        "broker_label": row.broker_label,
        "base_ccy": row.base_ccy,
        "status": row.status,
        "account_max_risk_pct": row.account_max_risk_pct,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "close_reason": row.close_reason,
        "close_note": row.close_note,
    }
