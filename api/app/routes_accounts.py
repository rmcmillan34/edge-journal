from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .db import get_db
from .deps import get_current_user
from .models import Account, User
from .schemas import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("", response_model=List[AccountOut])
def list_accounts(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    rows = db.query(Account).filter(Account.user_id == current.id).order_by(Account.name.asc()).all()
    return rows

@router.post("", response_model=AccountOut, status_code=201)
def create_account(body: AccountCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    exists = db.query(Account).filter(Account.user_id == current.id, Account.name == body.name).first()
    if exists:
        raise HTTPException(409, detail="Account name already exists")
    row = Account(user_id=current.id, name=body.name, broker_label=body.broker_label, base_ccy=body.base_ccy, status="active")
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.patch("/{account_id}", response_model=AccountOut)
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
    return row
