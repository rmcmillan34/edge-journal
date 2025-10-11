# api/app/routes_uploads.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Dict, List, Any
import csv
import io
from sqlalchemy.orm import Session
from .db import get_db
from .models import Upload, Trade, Account, Instrument
from datetime import datetime, timezone

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Minimal preset dictionary (we’ll expand later)
#TODO: Extract to a JSON or YAML file for configurability
PRESETS = {
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
            "Quantity": ["Qty", "Quantity", "Contracts"],
            "Entry Price": ["Entry price"],
            "Exit Price": ["Exit price"],
            "Fees": ["Commissions", "Fees"],
            "Net PnL": ["Profit", "PnL", "Realized PnL"],
            "ExternalTradeID": ["Trade #", "Order ID"],
            "Notes": ["Notes", "Comment"],
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

@router.post("")
async def upload_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid text encoding")

    f = io.StringIO(text)
    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    if not headers:
        raise HTTPException(status_code=400, detail="CSV appears to have no header row")

    preset = _detect_preset(headers)
    mapping = _build_mapping(preset, headers)
    missing = [c for c in CORE_FIELDS if c not in mapping]

    preview_rows = []
    rows = 0
    for i, row in enumerate(reader):
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


def _parse_dt(dt_str: str) -> datetime:
    try:
        dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)  # MVP: treat input as UTC
    except Exception as e:
        raise ValueError(f"Invalid datetime: {dt_str}") from e

def _build_trade_key(acct: str, sym: str, side: str, ot: str, qty: str, entry: str) -> str:
    return f"{acct}|{sym}|{side}|{ot}|{qty}|{entry}".lower().strip()

def _get_or_create_instrument(db: Session, symbol: str) -> Instrument:
    inst = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if inst:
        return inst
    inst = Instrument(symbol=symbol, asset_class=None)
    db.add(inst); db.flush()
    return inst

def _get_or_create_account(db: Session, name: str) -> Account:
    acct = db.query(Account).filter(Account.name == name).first()
    if acct:
        return acct
    acct = Account(name=name, status="active")
    db.add(acct); db.flush()
    return acct

@router.post("/commit")
async def commit_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content = await file.read()
    text = content.decode("utf-8", errors="replace")

    f = io.StringIO(text)
    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    if not headers:
        raise HTTPException(status_code=400, detail="CSV appears to have no header row")

    preset = _detect_preset(headers)
    mapping = _build_mapping(preset, headers)

    required_for_key = ["Account", "Symbol", "Side", "Open Time", "Quantity", "Entry Price"]
    missing_for_key = [c for c in required_for_key if c not in mapping]
    if missing_for_key:
        raise HTTPException(status_code=400, detail=f"Missing required fields for dedupe key: {missing_for_key}")

    upload = Upload(filename=file.filename, preset=preset, status="committed")
    db.add(upload); db.flush()

    inserted = updated = skipped = 0
    errors: List[Dict[str, Any]] = []

    for lineno, row in enumerate(reader, start=2):  # 1 is header
        try:
            account = (row.get(mapping["Account"], "") or "").strip()
            symbol = (row.get(mapping["Symbol"], "") or "").strip()
            side = (row.get(mapping["Side"], "") or "").strip().capitalize()
            open_time_str = (row.get(mapping["Open Time"], "") or "").strip()
            close_time_str = (row.get(mapping.get("Close Time",""), "") or "").strip()

            qty = (row.get(mapping.get("Quantity",""), "") or "0").strip()
            entry = (row.get(mapping.get("Entry Price",""), "") or "0").strip()
            exitp = (row.get(mapping.get("Exit Price",""), "") or "").strip()

            fees = (row.get(mapping.get("Fees",""), "") or "").strip()
            net = (row.get(mapping.get("Net PnL",""), "") or "").strip()
            extid = (row.get(mapping.get("ExternalTradeID",""), "") or "").strip()
            notes = (row.get(mapping.get("Notes",""), "") or "").strip()

            open_dt = _parse_dt(open_time_str)
            close_dt = _parse_dt(close_time_str) if close_time_str else None

            qty_f   = float(qty)   if qty   else None
            entry_f = float(entry) if entry else None
            exit_f  = float(exitp) if exitp else None
            fees_f  = float(fees)  if fees  not in ("", None) else None
            net_f   = float(net)   if net   not in ("", None) else None

            trade_key = _build_trade_key(account, symbol, side, open_time_str, qty, entry)

            acct = _get_or_create_account(db, account) if account else None
            inst = _get_or_create_instrument(db, symbol) if symbol else None

            existing = db.query(Trade).filter(Trade.trade_key == trade_key).first()
            if existing:
                existing.exit_price = exit_f
                existing.close_time_utc = close_dt
                existing.fees = fees_f
                existing.net_pnl = net_f
                existing.notes_md = notes or existing.notes_md
                existing.external_trade_id = extid or existing.external_trade_id
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
                ))
                inserted += 1

        except Exception as e:
            errors.append({"line": lineno, "reason": str(e)})
            skipped += 1

    db.commit()
    return {
        "detected_preset": preset,
        "mapping": mapping,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:20],
        "upload_id": upload.id,
    }