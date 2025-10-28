# api/app/routes_uploads.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from typing import Dict, List, Any
import csv
import io
import json
import os
from sqlalchemy.orm import Session
from .db import get_db
from .deps import get_optional_user, get_current_user
from .models import Upload, Trade, Account, Instrument, MappingPreset, User
from datetime import datetime, timezone
from sqlalchemy import and_
from .forex_utils import (
    is_forex_pair,
    detect_pip_location,
    calculate_pips,
    infer_lot_size_from_qty,
)
from .futures_utils import (
    is_futures_symbol,
    parse_futures_symbol,
    get_contract_specs,
    calculate_ticks,
    format_contract_month,
    get_expiration_estimate,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Minimal preset dictionary (we’ll expand later)
#TODO: Extract to a JSON or YAML file for configurability
PRESETS = {
    "ftmo": {
        "match": {"Open", "Close", "Symbol", "Profit"},
        "map": {
            "Account": ["Account", "Login"],
            "Symbol": ["Symbol", "Instrument"],
            "Side": ["Type", "Side", "Direction"],
            "Open Time": ["Open", "Open Time", "Time", "Entry Time", "OpenTime"],
            "Close Time": ["Close", "Close Time", "Exit Time", "CloseTime"],
            "Quantity": ["Qty", "Volume"],  # Map both Qty and Volume to Quantity
            "Entry Price": ["Open Price", "Price", "Price[1]", "Entry", "Price Open"],
            "Exit Price": ["Close Price", "Price[2]", "Exit", "Price Close"],
            "Fees": ["Commission", "Commissions"],  # Separate from Swap
            "Net PnL": ["Profit", "Net PnL", "NetProfit", "Net P/L"],
            "ExternalTradeID": ["Order", "Ticket", "Position ID"],
            "Notes": ["Comment", "Notes", "Note"],
            # Forex-specific fields
            "Volume": ["Volume", "Lot Size", "Lots"],
            "Pips": ["Pips", "Pip P&L"],
            "Swap": ["Swap", "Overnight Fee"],
            "SL": ["SL", "Stop Loss", "StopLoss"],
            "TP": ["TP", "Take Profit", "TakeProfit"],
        },
    },
    "ctrader": {
        "match": {"Open Time", "Close Time", "Symbol"},
        "map": {
            "Account": ["Account", "Account Name", "Login"],
            "Symbol": ["Symbol", "Instrument"],
            "Side": ["Side", "Type", "Direction"],
            "Open Time": ["Open Time", "Entry Time", "OpenTime"],
            "Close Time": ["Close Time", "Exit Time", "CloseTime"],
            "Quantity": ["Volume", "Lots", "Quantity", "Qty"],
            "Entry Price": ["Open Price", "Entry", "Price Open", "Entry Price"],
            "Exit Price": ["Close Price", "Exit", "Price Close", "Exit Price"],
            "Fees": ["Commission", "Fees", "Swap", "Commission+Swap"],
            "Net PnL": ["Net PnL", "Profit", "NetProfit", "Net P/L"],
            "ExternalTradeID": ["Ticket", "Trade ID", "Order", "Position ID"],
            "Notes": ["Comment", "Notes", "Note"],
        },
    },
    "mt5": {
        "match": {"Open Time", "Close Time", "Symbol", "Profit"},
        "map": {
            "Account": ["Account", "Login"],
            "Symbol": ["Symbol"],
            "Side": ["Type", "Side"],
            "Open Time": ["Open Time", "Time"],
            "Close Time": ["Close Time"],
            "Quantity": ["Volume", "Lots"],
            "Entry Price": ["Price", "Open Price"],
            "Exit Price": ["Close Price"],
            "Fees": ["Commission", "Swap"],
            "Net PnL": ["Profit"],
            "ExternalTradeID": ["Order", "Ticket"],
            "Notes": ["Comment"],
        },
    },
    "ninjatrader": {
        "match": {"Instrument", "Entry time", "Exit time"},
        "map": {
            "Account": ["Account"],
            "Symbol": ["Instrument"],
            "Side": ["Strategy", "Action", "Side"],
            "Open Time": ["Entry time"],
            "Close Time": ["Exit time"],
            "Quantity": ["Qty", "Quantity"],
            "Entry Price": ["Entry price"],
            "Exit Price": ["Exit price"],
            "Fees": ["Commissions", "Fees"],
            "Net PnL": ["Profit", "PnL", "Realized PnL"],
            "ExternalTradeID": ["Trade #", "Order ID"],
            "Notes": ["Notes", "Comment"],
            # Futures-specific fields
            "Contracts": ["Contracts", "Qty", "Quantity"],
            "Ticks": ["Ticks", "Points"],
        },
    },
    "tradovate": {
        "match": {"Contract", "Buy/Sell", "Exec Time"},
        "map": {
            "Account": ["Account", "Account Name"],
            "Symbol": ["Contract", "Instrument"],
            "Side": ["Buy/Sell", "B/S", "Side"],
            "Open Time": ["Exec Time", "Entry Time", "Time"],
            "Close Time": ["Exit Time", "Close Time"],
            "Quantity": ["Qty"],
            "Entry Price": ["Price", "Entry Price", "Fill Price"],
            "Exit Price": ["Exit Price", "Close Price"],
            "Fees": ["Fees", "Commission"],
            "Net PnL": ["Realized P&L", "Net P/L", "PnL"],
            "ExternalTradeID": ["Order ID", "ID"],
            "Notes": ["Notes"],
            # Futures-specific fields
            "Contracts": ["Qty", "Contracts"],
            "Ticks": ["Ticks", "Points"],
        },
    },
}

# Core fields we want to map to
CORE_FIELDS = [
    "Account",
    "Symbol",
    "Side",
    "Open Time",
    "Close Time",
    "Quantity",
    "Entry Price",
    "Exit Price",
    "Fees",
    "Net PnL",
    "ExternalTradeID",
    "Notes",
]

CANON_REQUIRED = ["Account","Symbol","Side","Open Time","Quantity","Entry Price"]

def _detect_preset(headers: List[str]) -> str:
    hset = set(headers)
    best = None
    best_score = -1
    for name, preset in PRESETS.items():
        score = len(hset.intersection(preset["match"]))
        if score > best_score:
            best_score = score
            best = name
    return best or "custom"

def _build_mapping(preset_name: str, headers: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    headers_lower = {h.lower(): h for h in headers}

    if preset_name in PRESETS:
        for target, synonyms in PRESETS[preset_name]["map"].items():
            for s in synonyms:
                h = headers_lower.get(s.lower())
                if h:
                    mapping[target] = h
                    break

    # Fallback: exact field name
    for field in CORE_FIELDS:
        if field in headers and field not in mapping:
            mapping[field] = field

    return mapping

def _unique_headers(headers: List[str]) -> List[str]:
    seen: dict[str, int] = {}
    out: List[str] = []
    for h in headers:
        cnt = seen.get(h, 0) + 1
        seen[h] = cnt
        if cnt == 1:
            out.append(h)
        else:
            out.append(f"{h}[{cnt}]")
    return out

@router.get("")
def list_uploads(db: Session = Depends(get_db), current: User = Depends(get_current_user), limit: int = 50, offset: int = 0):
    q = db.query(Upload).filter(Upload.user_id == current.id).order_by(Upload.created_at.desc()).offset(offset).limit(min(limit, 200))
    rows = q.all()
    out = []
    for u in rows:
        out.append({
            "id": u.id,
            "filename": u.filename,
            "preset": u.preset,
            "status": u.status,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "inserted_count": u.inserted_count or 0,
            "updated_count": u.updated_count or 0,
            "skipped_count": u.skipped_count or 0,
            "error_count": u.error_count or 0,
            "tz": getattr(u, "tz", None),
        })
    return out


@router.get("/{upload_id}")
def get_upload(upload_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    u = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current.id).first()
    if not u:
        raise HTTPException(404, detail="Upload not found")
    try:
        errs = json.loads(u.errors_json) if u.errors_json else []
    except Exception:
        errs = []
    return {
        "id": u.id,
        "filename": u.filename,
        "preset": u.preset,
        "tz": getattr(u, "tz", None),
        "status": u.status,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "inserted_count": u.inserted_count or 0,
        "updated_count": u.updated_count or 0,
        "skipped_count": u.skipped_count or 0,
        "error_count": u.error_count or 0,
        "errors": errs,
    }

MAX_UPLOAD_MB = float(os.environ.get("MAX_UPLOAD_MB", "20"))

@router.post("")
async def upload_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()
    if len(content) > int(MAX_UPLOAD_MB * 1024 * 1024):
        raise HTTPException(status_code=413, detail=f"File exceeds limit of {int(MAX_UPLOAD_MB)} MB")
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid text encoding")

    f = io.StringIO(text)
    row_reader = csv.reader(f)
    try:
        raw_headers = next(row_reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="CSV appears empty")
    headers = _unique_headers([h.strip() for h in raw_headers])
    # Build rows as dicts with unique headers (handles duplicate names)
    rows_list: list[dict[str, str]] = []
    for r in row_reader:
        d = {headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))}
        rows_list.append(d)
    if not headers:
        raise HTTPException(status_code=400, detail="CSV appears to have no header row")

    preset = _detect_preset(headers)
    mapping = _build_mapping(preset, headers)
    missing = [c for c in CORE_FIELDS if c not in mapping]

    preview_rows = []
    rows = 0
    for i, row in enumerate(rows_list):
        if i < 5:
            preview_rows.append({k: row.get(mapping.get(k, ""), "") for k in CORE_FIELDS if k in mapping})
        rows += 1

    plan = {
        "rows_total": rows,
        "rows_to_insert": rows,   # we’ll compute real upserts in commit stage
        "rows_to_update": 0,
        "rows_to_skip": 0,
    }

    return {
        "detected_preset": preset,
        "headers": headers,
        "mapping": mapping,
        "missing_fields": missing,
        "plan": plan,
        "preview": preview_rows,
    }


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

def _build_trade_key(acct: str, sym: str, side: str, ot: str, qty: str, entry: str) -> str:
    return f"{acct}|{sym}|{side}|{ot}|{qty}|{entry}".lower().strip()

def _get_or_create_instrument(db: Session, symbol: str) -> Instrument:
    inst = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if inst:
        # Update asset_class if not set
        if not inst.asset_class:
            if is_futures_symbol(symbol):
                inst.asset_class = 'futures'
                # Set futures metadata
                parsed = parse_futures_symbol(symbol)
                if parsed:
                    inst.contract_month = format_contract_month(symbol)
                    inst.expiration_date = get_expiration_estimate(symbol)
                    specs = get_contract_specs(parsed['root'])
                    if specs:
                        inst.contract_size = specs['contract_size']
                        inst.tick_size = specs['tick_size']
                        inst.tick_value = specs['tick_value']
                db.flush()
            elif is_forex_pair(symbol):
                inst.asset_class = 'forex'
                inst.pip_location = detect_pip_location(symbol)
                db.flush()
        return inst

    # Create new instrument - detect asset class
    asset_class = 'equity'  # default
    pip_loc = None
    contract_size = None
    tick_size = None
    tick_value = None
    contract_month = None
    expiration_date = None

    if is_futures_symbol(symbol):
        asset_class = 'futures'
        parsed = parse_futures_symbol(symbol)
        if parsed:
            contract_month = format_contract_month(symbol)
            expiration_date = get_expiration_estimate(symbol)
            specs = get_contract_specs(parsed['root'])
            if specs:
                contract_size = specs['contract_size']
                tick_size = specs['tick_size']
                tick_value = specs['tick_value']
    elif is_forex_pair(symbol):
        asset_class = 'forex'
        pip_loc = detect_pip_location(symbol)

    inst = Instrument(
        symbol=symbol,
        asset_class=asset_class,
        pip_location=pip_loc,
        contract_size=contract_size,
        tick_size=tick_size,
        tick_value=tick_value,
        contract_month=contract_month,
        expiration_date=expiration_date,
    )
    db.add(inst)
    db.flush()
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

def _parse_number(val: str) -> float | None:
    if val is None:
        return None
    s = val.strip()
    if s == "":
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace(",", "")
    try:
        f = float(s)
        return -f if neg else f
    except Exception as e:
        raise ValueError(f"Invalid number: {val}") from e

def _norm_qty_str(x: float | None) -> str:
    if x is None:
        return ""
    return f"{round(x, 2):.2f}"

def _norm_price_str(x: float | None) -> str:
    if x is None:
        return ""
    return f"{round(x, 5):.5f}"

@router.post("/commit")
async def commit_csv(
    file: UploadFile = File(...),
    mapping: str | None = Form(None),
    preset_name: str | None = Form(None),
    save_as: str | None = Form(None),
    account_name: str | None = Form(None),
    account_id: int | None = Form(None),
    tz: str | None = Form(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()
    if len(content) > int(MAX_UPLOAD_MB * 1024 * 1024):
        raise HTTPException(status_code=413, detail=f"File exceeds limit of {int(MAX_UPLOAD_MB)} MB")
    text = content.decode("utf-8", errors="replace")

    f = io.StringIO(text)
    row_reader = csv.reader(f)
    try:
        raw_headers = next(row_reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="CSV appears empty")
    headers = _unique_headers([h.strip() for h in raw_headers])
    if not headers:
        raise HTTPException(status_code=400, detail="CSV appears to have no header row")

    preset = _detect_preset(headers)
    auto_map = _build_mapping(preset, headers)
    # Resolve mapping from auto + optional preset + optional override
    allow_missing_account = bool(account_name or account_id)
    final_map = resolve_mapping(db, getattr(current, "id", None), headers, preset_name, mapping, auto_map, allow_missing_account=allow_missing_account)

    required_for_key = ["Account", "Symbol", "Side", "Open Time", "Quantity", "Entry Price"]
    missing_for_key = [c for c in required_for_key if c not in final_map and not (c == "Account" and allow_missing_account)]
    if missing_for_key:
        raise HTTPException(status_code=400, detail=f"Missing required fields for dedupe key: {missing_for_key}")

    upload = Upload(user_id=current.id, filename=file.filename, preset=preset, status="committed")
    upload.tz = tz
    db.add(upload); db.flush()

    inserted = updated = skipped = 0
    errors: List[Dict[str, Any]] = []

    for lineno, raw in enumerate(row_reader, start=2):  # 1 is header
        row = {headers[i]: (raw[i] if i < len(raw) else "") for i in range(len(headers))}
        try:
            if "Account" in final_map:
                account = (row.get(final_map["Account"], "") or "").strip()
            else:
                account = (account_name or "").strip()
            symbol = (row.get(final_map["Symbol"], "") or "").strip()
            side = (row.get(final_map["Side"], "") or "").strip().capitalize()
            open_time_str = (row.get(final_map["Open Time"], "") or "").strip()
            close_time_str = (row.get(final_map.get("Close Time",""), "") or "").strip()

            qty = (row.get(final_map.get("Quantity",""), "") or "0").strip()
            entry = (row.get(final_map.get("Entry Price",""), "") or "0").strip()
            exitp = (row.get(final_map.get("Exit Price",""), "") or "").strip()

            fees = (row.get(final_map.get("Fees",""), "") or "").strip()
            net = (row.get(final_map.get("Net PnL",""), "") or "").strip()
            extid = (row.get(final_map.get("ExternalTradeID",""), "") or "").strip()
            notes = (row.get(final_map.get("Notes",""), "") or "").strip()

            # Forex-specific fields
            lot_size_str = (row.get(final_map.get("Lot Size",""), "") or row.get(final_map.get("Volume",""), "") or "").strip()
            pips_str = (row.get(final_map.get("Pips",""), "") or "").strip()
            swap_str = (row.get(final_map.get("Swap",""), "") or "").strip()
            stop_loss_str = (row.get(final_map.get("Stop Loss",""), "") or row.get(final_map.get("SL",""), "") or "").strip()
            take_profit_str = (row.get(final_map.get("Take Profit",""), "") or row.get(final_map.get("TP",""), "") or "").strip()

            # Futures-specific fields
            contracts_str = (row.get(final_map.get("Contracts",""), "") or "").strip()
            ticks_str = (row.get(final_map.get("Ticks",""), "") or "").strip()

            open_dt = _parse_dt(open_time_str, tz)
            close_dt = _parse_dt(close_time_str, tz) if close_time_str else None

            qty_f   = _parse_number(qty)
            entry_f = _parse_number(entry)
            exit_f  = _parse_number(exitp)
            fees_f  = _parse_number(fees)
            net_f   = _parse_number(net)

            # Parse forex fields
            lot_size_direct = _parse_number(lot_size_str)
            pips_f = _parse_number(pips_str)
            swap_f = _parse_number(swap_str)
            stop_loss_f = _parse_number(stop_loss_str)
            take_profit_f = _parse_number(take_profit_str)

            # Parse futures fields
            contracts_f = int(_parse_number(contracts_str)) if contracts_str and _parse_number(contracts_str) else None
            ticks_f = _parse_number(ticks_str)

            # Resolve account row → model
            acct = None
            if account_id:
                acct = db.query(Account).filter(Account.id == account_id, Account.user_id == current.id).first()
                if not acct:
                    raise ValueError("Account ID not found")
                # M6: reject trades for closed accounts
                if acct.status == "closed":
                    raise ValueError(f"Account '{acct.name}' is closed. Please reopen or select a different account.")
            elif account:
                acct = _get_or_create_account(db, account, current.id)
                # M6: reject trades for closed accounts
                if acct and acct.status == "closed":
                    raise ValueError(f"Account '{acct.name}' is closed. Please reopen or select a different account.")

            # Build a stable dedupe key using normalized values (UTC time, rounded qty/price)
            ot_utc_str = open_dt.strftime("%Y-%m-%d %H:%M:%S")
            qty_norm = _norm_qty_str(qty_f)
            entry_norm = _norm_price_str(entry_f)
            trade_key = _build_trade_key(account or (acct.name if acct else ""), symbol, side, ot_utc_str, qty_norm, entry_norm)

            inst = _get_or_create_instrument(db, symbol) if symbol else None

            # Smart fallback for lot_size and pip calculation for forex trades
            lot_size_final = None
            pips_final = pips_f
            contracts_final = contracts_f
            ticks_final = ticks_f

            if inst and inst.asset_class == 'forex':
                # Lot size: use direct value or calculate from qty_units
                if lot_size_direct is not None:
                    lot_size_final = lot_size_direct
                elif qty_f is not None:
                    lot_size_final = infer_lot_size_from_qty(qty_f, symbol)

                # Pips: calculate if not provided and we have entry/exit prices
                if pips_final is None and entry_f is not None and exit_f is not None:
                    pips_final = calculate_pips(
                        symbol,
                        entry_f,
                        exit_f,
                        side,
                        inst.pip_location
                    )

            elif inst and inst.asset_class == 'futures':
                # Contracts: use qty_units if contracts not provided
                if contracts_final is None and qty_f is not None:
                    contracts_final = int(qty_f)

                # Ticks: calculate if not provided and we have entry/exit prices
                if ticks_final is None and entry_f is not None and exit_f is not None and inst.tick_size:
                    ticks_final = calculate_ticks(
                        entry_f,
                        exit_f,
                        side,
                        float(inst.tick_size)
                    )

            existing = db.query(Trade).filter(Trade.trade_key == trade_key).first()
            if existing:
                existing.exit_price = exit_f
                existing.close_time_utc = close_dt
                existing.fees = fees_f
                existing.net_pnl = net_f
                existing.notes_md = notes or existing.notes_md
                existing.external_trade_id = extid or existing.external_trade_id
                # Update forex fields
                existing.lot_size = lot_size_final
                existing.pips = pips_final
                existing.swap = swap_f
                existing.stop_loss = stop_loss_f
                existing.take_profit = take_profit_f
                # Update futures fields
                existing.contracts = contracts_final
                existing.ticks = ticks_final
                updated += 1
            else:
                db.add(Trade(
                    account_id=acct.id if acct else None,
                    instrument_id=inst.id if inst else None,
                    external_trade_id=extid,
                    side=side,
                    qty_units=qty_f,
                    entry_price=entry_f,
                    exit_price=exit_f,
                    open_time_utc=open_dt,
                    close_time_utc=close_dt,
                    gross_pnl=None,
                    fees=fees_f,
                    net_pnl=net_f,
                    notes_md=notes,
                    source_upload_id=upload.id,
                    trade_key=trade_key,
                    version=1,
                    # Forex fields
                    lot_size=lot_size_final,
                    pips=pips_final,
                    swap=swap_f,
                    stop_loss=stop_loss_f,
                    take_profit=take_profit_f,
                    # Futures fields
                    contracts=contracts_final,
                    ticks=ticks_final,
                ))
                inserted += 1

        except Exception as e:
            errors.append({"line": lineno, "reason": str(e)})
            skipped += 1

    # persist summary on the upload row
    upload.inserted_count = inserted
    upload.updated_count = updated
    upload.skipped_count = skipped
    upload.error_count = len(errors)
    # store a trimmed error list as JSON (up to 100 entries)
    try:
        upload.errors_json = json.dumps(errors[:100]) if errors else None
    except Exception:
        upload.errors_json = None

    # Optional: save mapping as a user preset on success
    if save_as:
        try:
            exists = db.query(MappingPreset).filter(
                MappingPreset.user_id == current.id,
                MappingPreset.name == save_as,
            ).first()
            if not exists:
                pr = MappingPreset(
                    user_id=current.id,
                    name=save_as,
                    headers_json=json.dumps(headers),
                    mapping_json=json.dumps(final_map),
                )
                db.add(pr)
        except Exception:
            pass  # don't fail commit if preset save fails

    db.commit()
    return {
        "detected_preset": preset,
        "mapping": final_map,
        "inserted_count": inserted,
        "updated_count": updated,
        "skipped_count": skipped,
        "error_count": len(errors),
        "errors": errors[:20],
        "upload_id": upload.id,
    }

def resolve_mapping(db: Session, user_id: int | None, headers: list[str], preset_name: str | None, override_json: str | None, auto_mapping: dict, *, allow_missing_account: bool = False) -> dict:
    final = dict(auto_mapping)  # start from detected
    # apply preset if present
    if preset_name and user_id:
        pr = db.query(MappingPreset).filter(MappingPreset.user_id == user_id, MappingPreset.name == preset_name).first()
        if not pr:
            raise HTTPException(404, detail="Preset not found")
        preset_map = json.loads(pr.mapping_json)
        final.update(preset_map)
    # apply override
    if override_json:
        try:
            override = json.loads(override_json)
            if not isinstance(override, dict):
                raise ValueError("mapping override must be an object")
            final.update(override)
        except Exception as e:
            raise HTTPException(400, detail=f"Invalid mapping JSON: {e}")

    hdrs = set(headers)
    required = list(CANON_REQUIRED)
    if allow_missing_account and "Account" in required:
        required.remove("Account")
    missing = [c for c in required if c not in final]
    invalid = [k for k,v in final.items() if v not in hdrs]
    if missing:
        raise HTTPException(400, detail=f"Missing required canonical fields: {missing}")
    if invalid:
        raise HTTPException(400, detail=f"Mapping points to headers not present: {invalid}")
    return final


@router.post("/preview")
async def preview_csv(
    file: UploadFile = File(...),
    mapping: str | None = Form(None),         # JSON string override
    preset_name: str | None = Form(None),
    save_as: str | None = Form(None),
    account_name: str | None = Form(None),
    account_id: int | None = Form(None),
    tz: str | None = Form(None),
    db: Session = Depends(get_db),
    current: User | None = Depends(get_optional_user),
):
    content = await file.read()
    if len(content) > int(MAX_UPLOAD_MB * 1024 * 1024):
        raise HTTPException(status_code=413, detail=f"File exceeds limit of {int(MAX_UPLOAD_MB)} MB")
    text = content.decode("utf-8", errors="replace")
    f = io.StringIO(text)
    row_reader = csv.reader(f)
    try:
        raw_headers = next(row_reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="CSV appears empty")
    headers = _unique_headers([h.strip() for h in raw_headers])
    if not headers:
        raise HTTPException(status_code=400, detail="CSV appears to have no header row")

    preset = _detect_preset(headers)
    auto_map = _build_mapping(preset, headers)
    allow_missing_account = bool(account_name or account_id)
    resolved = resolve_mapping(db, getattr(current, "id", None), headers, preset_name, mapping, auto_map, allow_missing_account=allow_missing_account)

    rows_total = rows_valid = rows_invalid = 0
    preview = []
    for lineno, raw in enumerate(row_reader, start=2):
        rows_total += 1
        row = {headers[i]: (raw[i] if i < len(raw) else "") for i in range(len(headers))}
        try:
            # minimal parse using resolved mapping
            required = ["Symbol","Side","Open Time","Quantity","Entry Price"]
            if "Account" in resolved:
                _ = row[resolved["Account"]]
            for k in required:
                _ = row[resolved[k]]
            # try parse datetime with tz
            _ = _parse_dt(row[resolved["Open Time"]], tz)
            rows_valid += 1
            if len(preview) < 5:  # first 5 rows
                preview.append({k: row.get(v, "") for k, v in resolved.items()})
        except Exception:
            rows_invalid += 1

    return {
        "detected_preset": preset,
        "applied_mapping": resolved,
        "plan": {"rows_total": rows_total, "rows_valid": rows_valid, "rows_invalid": rows_invalid},
        "preview": preview,
        "tz": tz,
    }


@router.delete("/{upload_id}")
def delete_upload(upload_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    # Ensure upload belongs to current user
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current.id).first()
    if not upload:
        raise HTTPException(404, detail="Upload not found")

    # Delete trades that came from this upload (scoped to user's accounts for safety)
    # Join via Account to guarantee ownership
    trade_q = db.query(Trade).join(Account, Account.id == Trade.account_id).filter(
        Trade.source_upload_id == upload.id,
        Account.user_id == current.id,
    )
    deleted_trades = 0
    for t in trade_q.all():
        db.delete(t)
        deleted_trades += 1

    # Finally delete the upload record
    db.delete(upload)
    db.commit()
    return {"deleted_trades": deleted_trades, "deleted_upload": upload_id}


@router.get("/{upload_id}/errors.csv")
def download_errors_csv(upload_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == current.id).first()
    if not upload:
        raise HTTPException(404, detail="Upload not found")
    if not upload.errors_json:
        # No errors recorded; return an empty CSV with header
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("line,reason\n", media_type="text/csv")
    try:
        errs = json.loads(upload.errors_json) or []
    except Exception:
        errs = []
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["line", "reason"])
    for e in errs:
        w.writerow([e.get("line", ""), e.get("reason", "")])
    csv_text = output.getvalue()
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(csv_text, media_type="text/csv")
