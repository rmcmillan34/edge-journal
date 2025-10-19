from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

from .db import get_db
from .deps import get_current_user
from .models import Trade, Account, Instrument

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
def get_metrics(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) inclusive"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD) inclusive"),
    symbol: Optional[str] = None,
    account: Optional[str] = None,
    tz: Optional[str] = Query(None, description="IANA timezone for daily grouping (e.g., UTC, Australia/Sydney)"),
):
    # Base query filtered to user's trades
    q = db.query(
        Trade.id,
        Trade.net_pnl,
        Trade.open_time_utc,
        Trade.close_time_utc,
        Trade.reviewed,
        Account.name.label("account_name"),
        Instrument.symbol.label("symbol"),
    ).join(Account, Account.id == Trade.account_id, isouter=True).join(Instrument, Instrument.id == Trade.instrument_id, isouter=True)
    q = q.filter(Account.user_id == current.id)

    # Date range on realized date (close if available, else open)
    # Date parsing for local-day filtering
    def parse_date_only(d: str) -> date:
        return datetime.strptime(d, "%Y-%m-%d").date()

    start_d: Optional[date] = parse_date_only(start) if start else None
    end_d: Optional[date] = parse_date_only(end) if end else None

    rows = q.all()

    # Choose timezone for grouping
    zinfo: Optional[ZoneInfo] = None
    if tz and tz.upper() != "UTC":
        try:
            zinfo = ZoneInfo(tz)
        except Exception:
            zinfo = None

    def event_dt(r):
        return (r.close_time_utc or r.open_time_utc)

    filtered: List = []
    local_dt_list: List[datetime] = []
    for r in rows:
        dt = event_dt(r)
        local_dt = dt.astimezone(zinfo) if zinfo else dt
        local_day = local_dt.date()
        if start_d and local_day < start_d:
            continue
        if end_d and local_day > end_d:
            continue
        if symbol and (not (r.symbol or "").lower().__contains__(symbol.lower())):
            continue
        if account and (not (r.account_name or "").lower().__contains__(account.lower())):
            continue
        filtered.append(r)
        local_dt_list.append(local_dt)

    trades_total = len(filtered)
    wins = sum(1 for r in filtered if (r.net_pnl or 0) > 0)
    losses = sum(1 for r in filtered if (r.net_pnl or 0) < 0)
    net_pnl_sum = float(sum((r.net_pnl or 0.0) for r in filtered))
    denom = (wins + losses) or 0
    win_rate = (wins / denom) if denom else None
    unreviewed = sum(1 for r in filtered if not bool(getattr(r, "reviewed", False)))

    # Daily equity (by date key YYYY-MM-DD)
    daily = {}
    for r, d in zip(filtered, local_dt_list):
        key = d.strftime("%Y-%m-%d")
        daily[key] = daily.get(key, 0.0) + float(r.net_pnl or 0.0)
    # Sort by date
    dates = sorted(daily.keys())
    equity_curve = []
    cum = 0.0
    for k in dates:
        cum += daily[k]
        equity_curve.append({"date": k, "net_pnl": round(daily[k], 2), "equity": round(cum, 2)})

    return {
        "trades_total": trades_total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "net_pnl_sum": round(net_pnl_sum, 2),
        "equity_curve": equity_curve,
        "unreviewed_count": unreviewed,
    }
