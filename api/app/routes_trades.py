from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from .db import get_db
from .deps import get_current_user
from .models import Trade, Account, Instrument
from .schemas import TradeOut, TradeCreate, TradeUpdate
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/trades", tags=["trades"])

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
    sort: Optional[str] = Query(None, description="Sort by field, e.g., open_time_utc:desc, net_pnl:asc, symbol:asc"),
):
    q = db.query(
        Trade.id,
        Account.name.label("account_name"),
        Instrument.symbol.label("symbol"),
        Trade.side,
        Trade.qty_units,
        Trade.entry_price,
        Trade.exit_price,
        Trade.open_time_utc,
        Trade.close_time_utc,
        Trade.net_pnl,
        Trade.external_trade_id,
    ).outerjoin(Account, Account.id == Trade.account_id).outerjoin(Instrument, Instrument.id == Trade.instrument_id)
    q = q.filter(Account.user_id == current.id)

    if symbol:
        q = q.filter(Instrument.symbol.ilike(f"%{symbol}%"))
    if account:
        q = q.filter(Account.name.ilike(f"%{account}%"))

    # Optional date filters (on open_time_utc)
    def parse_date(d: str) -> datetime:
        return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if start:
        try:
            start_dt = parse_date(start)
            q = q.filter(Trade.open_time_utc >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = parse_date(end) + timedelta(days=1)  # exclusive next day
            q = q.filter(Trade.open_time_utc < end_dt)
        except Exception:
            pass

    # Sorting
    sort_expr = Trade.open_time_utc.desc()
    if sort:
        try:
            field, _, direction = sort.partition(":")
            direction = (direction or "desc").lower()
            field_map = {
                "open_time_utc": Trade.open_time_utc,
                "close_time_utc": Trade.close_time_utc,
                "net_pnl": Trade.net_pnl,
                "entry_price": Trade.entry_price,
                "exit_price": Trade.exit_price,
                "symbol": Instrument.symbol,
                "account": Account.name,
            }
            col = field_map.get(field)
            if col is not None:
                sort_expr = col.desc() if direction == "desc" else col.asc()
        except Exception:
            pass

    q = q.order_by(sort_expr).offset(offset).limit(limit)

    rows = q.all()
    out: List[TradeOut] = []
    for r in rows:
        out.append(TradeOut(
            id=r.id,
            account_name=r.account_name,
            symbol=r.symbol,
            side=r.side,
            qty_units=r.qty_units,
            entry_price=r.entry_price,
            exit_price=r.exit_price,
            open_time_utc=r.open_time_utc.isoformat() if r.open_time_utc else None,
            close_time_utc=r.close_time_utc.isoformat() if r.close_time_utc else None,
            net_pnl=r.net_pnl,
            external_trade_id=r.external_trade_id,
        ))
    return out


@router.get("/symbols", response_model=List[str])
def list_symbols(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    account: Optional[str] = None,
):
    q = db.query(Instrument.symbol).join(Trade, Trade.instrument_id == Instrument.id).join(Account, Account.id == Trade.account_id)
    q = q.filter(Account.user_id == current.id)
    if account:
        q = q.filter(Account.name.ilike(f"%{account}%"))
    rows = q.distinct().order_by(Instrument.symbol.asc()).all()
    return [r[0] for r in rows if r[0]]


def _parse_dt(dt_str: str, tz_name: str | None = None) -> datetime:
    try:
        dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
        if tz_name and tz_name.upper() != "UTC":
            try:
                from zoneinfo import ZoneInfo
                z = ZoneInfo(tz_name)
            except Exception as e:
                raise ValueError(f"Unknown timezone: {tz_name}") from e
            local = dt.replace(tzinfo=z)
            return local.astimezone(timezone.utc)
        return dt.replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"Invalid datetime: {dt_str}") from e


def _norm_qty_str(x: float | None) -> str:
    if x is None:
        return ""
    return f"{round(x, 2):.2f}"


def _norm_price_str(x: float | None) -> str:
    if x is None:
        return ""
    return f"{round(x, 5):.5f}"


def _build_trade_key(acct: str, sym: str, side: str, ot: str, qty: str, entry: str) -> str:
    return f"{acct}|{sym}|{side}|{ot}|{qty}|{entry}".lower().strip()


def _get_or_create_instrument(db: Session, symbol: str) -> Instrument:
    inst = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if inst:
        return inst
    inst = Instrument(symbol=symbol, asset_class=None)
    db.add(inst); db.flush()
    return inst


def _get_or_create_account(db: Session, name: str, user_id: int | None = None) -> Account:
    q = db.query(Account).filter(Account.name == name)
    if user_id:
        q = q.filter(Account.user_id == user_id)
    acct = q.first()
    if acct:
        return acct
    acct = Account(user_id=user_id, name=name, status="active")
    db.add(acct); db.flush()
    return acct


@router.post("", response_model=TradeOut)
def create_trade(body: TradeCreate, db: Session = Depends(get_db), current = Depends(get_current_user)):
    # Validate side
    side = body.side.strip().capitalize()
    if side not in ("Buy", "Sell"):
        raise HTTPException(400, detail="side must be 'Buy' or 'Sell'")

    # Resolve account
    acct = None
    if body.account_id is not None:
        acct = db.query(Account).filter(Account.id == body.account_id, Account.user_id == current.id).first()
        if not acct:
            raise HTTPException(404, detail="Account not found")
    elif body.account_name:
        acct = _get_or_create_account(db, body.account_name.strip(), current.id)
    else:
        raise HTTPException(400, detail="Provide account_id or account_name")

    # Instrument
    inst = _get_or_create_instrument(db, body.symbol.strip())

    # Parse datetimes (UTC)
    ot = _parse_dt(body.open_time, body.tz)
    ct = _parse_dt(body.close_time, body.tz) if body.close_time else None

    # Build dedupe key consistent with CSV commit
    ot_utc_str = ot.strftime("%Y-%m-%d %H:%M:%S")
    qty_norm = _norm_qty_str(body.qty_units)
    entry_norm = _norm_price_str(body.entry_price)
    trade_key = _build_trade_key(acct.name, inst.symbol, side, ot_utc_str, qty_norm, entry_norm)

    existing = db.query(Trade).filter(Trade.trade_key == trade_key).first()
    if existing:
        existing.exit_price = body.exit_price
        existing.close_time_utc = ct
        existing.fees = body.fees
        existing.net_pnl = body.net_pnl
        existing.notes_md = body.notes_md or existing.notes_md
        db.commit()
        return TradeOut(
            id=existing.id,
            account_name=acct.name,
            symbol=inst.symbol,
            side=existing.side,
            qty_units=existing.qty_units,
            entry_price=existing.entry_price,
            exit_price=existing.exit_price,
            open_time_utc=existing.open_time_utc.isoformat(),
            close_time_utc=existing.close_time_utc.isoformat() if existing.close_time_utc else None,
            net_pnl=existing.net_pnl,
            external_trade_id=existing.external_trade_id,
        )

    row = Trade(
        account_id=acct.id,
        instrument_id=inst.id,
        external_trade_id=None,
        side=side,
        qty_units=body.qty_units,
        entry_price=body.entry_price,
        exit_price=body.exit_price,
        open_time_utc=ot,
        close_time_utc=ct,
        gross_pnl=None,
        fees=body.fees,
        net_pnl=body.net_pnl,
        notes_md=body.notes_md,
        source_upload_id=None,
        trade_key=trade_key,
        version=1,
    )
    db.add(row); db.commit(); db.refresh(row)
    return TradeOut(
        id=row.id,
        account_name=acct.name,
        symbol=inst.symbol,
        side=row.side,
        qty_units=row.qty_units,
        entry_price=row.entry_price,
        exit_price=row.exit_price,
        open_time_utc=row.open_time_utc.isoformat(),
        close_time_utc=row.close_time_utc.isoformat() if row.close_time_utc else None,
        net_pnl=row.net_pnl,
        external_trade_id=row.external_trade_id,
    )


@router.patch("/{trade_id}", response_model=TradeOut)
def update_trade(trade_id: int, body: TradeUpdate, db: Session = Depends(get_db), current = Depends(get_current_user)):
    # Ensure ownership via Account
    q = db.query(Trade, Account.name.label("account_name"), Instrument.symbol.label("symbol")).\
        join(Account, Account.id == Trade.account_id, isouter=True).\
        join(Instrument, Instrument.id == Trade.instrument_id, isouter=True).\
        filter(Trade.id == trade_id, Account.user_id == current.id)
    row = q.first()
    if not row:
        raise HTTPException(404, detail="Trade not found")
    t, account_name, symbol = row
    if body.notes_md is not None:
        t.notes_md = body.notes_md
    if body.fees is not None:
        t.fees = body.fees
    if body.net_pnl is not None:
        t.net_pnl = body.net_pnl
    db.commit(); db.refresh(t)
    return TradeOut(
        id=t.id,
        account_name=account_name,
        symbol=symbol,
        side=t.side,
        qty_units=t.qty_units,
        entry_price=t.entry_price,
        exit_price=t.exit_price,
        open_time_utc=t.open_time_utc.isoformat() if t.open_time_utc else None,
        close_time_utc=t.close_time_utc.isoformat() if t.close_time_utc else None,
        net_pnl=t.net_pnl,
        external_trade_id=t.external_trade_id,
    )


@router.delete("/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db), current = Depends(get_current_user)):
    # Ensure ownership via Account and collect restore fields
    row = db.query(
        Trade.id,
        Account.name.label("account_name"),
        Instrument.symbol.label("symbol"),
        Trade.side,
        Trade.qty_units,
        Trade.entry_price,
        Trade.exit_price,
        Trade.open_time_utc,
        Trade.close_time_utc,
        Trade.fees,
        Trade.net_pnl,
        Trade.notes_md,
    ).join(Account, Account.id == Trade.account_id, isouter=True).join(Instrument, Instrument.id == Trade.instrument_id, isouter=True).\
      filter(Trade.id == trade_id, Account.user_id == current.id).first()
    if not row:
        raise HTTPException(404, detail="Trade not found")

    # Build restore payload before delete
    rp = {
        "account_name": row.account_name,
        "symbol": row.symbol,
        "side": row.side,
        "open_time": row.open_time_utc.strftime("%Y-%m-%d %H:%M:%S") if row.open_time_utc else None,
        "close_time": row.close_time_utc.strftime("%Y-%m-%d %H:%M:%S") if row.close_time_utc else None,
        "qty_units": row.qty_units,
        "entry_price": row.entry_price,
        "exit_price": row.exit_price,
        "fees": row.fees,
        "net_pnl": row.net_pnl,
        "notes_md": row.notes_md,
        "tz": "UTC",
    }
    t = db.query(Trade).filter(Trade.id == trade_id).first()
    db.delete(t); db.commit()
    return {"deleted": trade_id, "restore_payload": rp}
