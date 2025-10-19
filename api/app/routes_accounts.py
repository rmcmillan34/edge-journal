from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .db import get_db
from .deps import get_current_user
from .models import Account, User
from .schemas import AccountCreate, AccountOut

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
