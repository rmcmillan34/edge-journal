from fastapi import APIRouter, Depends, Query
import json
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

from .db import get_db
from .deps import get_current_user
from .models import Trade, Account, Instrument, PlaybookResponse, PlaybookTemplate, UserTradingRules

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


@router.get("/calendar")
def get_calendar(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    start: str = Query(..., description="Start date (YYYY-MM-DD) inclusive"),
    end: str = Query(..., description="End date (YYYY-MM-DD) inclusive"),
    tz: Optional[str] = Query(None, description="IANA timezone for daily grouping (e.g., UTC, Australia/Sydney)"),
):
    # Parse dates
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    end_d = datetime.strptime(end, "%Y-%m-%d").date()

    # Timezone
    zinfo: Optional[ZoneInfo] = None
    if tz and tz.upper() != "UTC":
        try:
            zinfo = ZoneInfo(tz)
        except Exception:
            zinfo = None

    # Load trades for user within range (by local day)
    q = db.query(
        Trade.id,
        Trade.net_pnl,
        Trade.open_time_utc,
        Trade.close_time_utc,
        Trade.account_id,
    ).join(Account, Account.id == Trade.account_id, isouter=True).filter(Account.user_id == current.id)

    trades = q.all()

    def event_local_day(r) -> date:
        dt = (r.close_time_utc or r.open_time_utc)
        local_dt = dt.astimezone(zinfo) if zinfo else dt
        return local_dt.date()

    # Prepare per-day buckets
    days: Dict[str, Dict] = {}
    for r in trades:
        day = event_local_day(r)
        if day < start_d or day > end_d:
            continue
        key = day.strftime("%Y-%m-%d")
        bucket = days.setdefault(key, {"date": key, "trades": 0, "net_pnl": 0.0, "breaches": []})
        bucket["trades"] += 1
        bucket["net_pnl"] += float(r.net_pnl or 0.0)

    # Loss streak per-day (intra-day)
    # Build mapping day -> list of trade pnls ordered by close time
    day_trades: Dict[str, List[Tuple[datetime, float, int]]] = {}
    for r in trades:
        day = event_local_day(r)
        if day < start_d or day > end_d:
            continue
        key = day.strftime("%Y-%m-%d")
        tdt = (r.close_time_utc or r.open_time_utc)
        day_trades.setdefault(key, []).append((tdt, float(r.net_pnl or 0.0), r.account_id or 0))
    for key, arr in day_trades.items():
        arr.sort(key=lambda x: x[0])

    # Load trading rules (defaults if none)
    rules = db.query(UserTradingRules).filter(UserTradingRules.user_id == current.id).first()
    max_losses_row_day = rules.max_losses_row_day if rules else 3
    max_losing_days_streak_week = rules.max_losing_days_streak_week if rules else 2
    max_losing_weeks_streak_month = rules.max_losing_weeks_streak_month if rules else 2

    # Compute intra-day loss streak breach
    for key, arr in day_trades.items():
        streak = 0
        max_streak = 0
        for _, pnl, _ in arr:
            if pnl < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        if max_streak > max_losses_row_day:
            days.setdefault(key, {"date": key, "trades": 0, "net_pnl": 0.0, "breaches": []})
            if "loss_streak_day" not in days[key]["breaches"]:
                days[key]["breaches"].append("loss_streak_day")

    # Weekly losing-day streaks within ISO week
    # Build day -> losing boolean
    day_lose_flag: Dict[date, bool] = {}
    for key, bucket in days.items():
        d = datetime.strptime(key, "%Y-%m-%d").date()
        day_lose_flag[d] = bucket["net_pnl"] < 0

    # Group by ISO week
    weeks: Dict[Tuple[int, int], List[date]] = {}
    cur = start_d
    while cur <= end_d:
        iso = cur.isocalendar()
        weeks.setdefault((iso[0], iso[1]), []).append(cur)
        cur += timedelta(days=1)

    for iso, dlist in weeks.items():
        dlist.sort()
        streak: List[date] = []
        for d in dlist:
            losing = day_lose_flag.get(d, False)
            if losing:
                streak.append(d)
            else:
                if len(streak) > max_losing_days_streak_week:
                    for sd in streak:
                        key = sd.strftime("%Y-%m-%d")
                        days.setdefault(key, {"date": key, "trades": 0, "net_pnl": 0.0, "breaches": []})
                        if "losing_days_week" not in days[key]["breaches"]:
                            days[key]["breaches"].append("losing_days_week")
                streak = []
        if len(streak) > max_losing_days_streak_week:
            for sd in streak:
                key = sd.strftime("%Y-%m-%d")
                days.setdefault(key, {"date": key, "trades": 0, "net_pnl": 0.0, "breaches": []})
                if "losing_days_week" not in days[key]["breaches"]:
                    days[key]["breaches"].append("losing_days_week")

    # Monthly losing-week streaks (calendar month) based on weekly sums
    # Build per-week sum within month buckets
    month_weeks: Dict[Tuple[int, int], float] = {}
    for key, bucket in days.items():
        d = datetime.strptime(key, "%Y-%m-%d").date()
        iso = d.isocalendar()
        month_weeks.setdefault((iso[0], iso[1]), 0.0)
        month_weeks[(iso[0], iso[1])] += bucket["net_pnl"]

    # Group by calendar month -> ordered list of iso weeks present in range
    months: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    cur = start_d
    while cur <= end_d:
        months.setdefault((cur.year, cur.month), [])
        iso = cur.isocalendar()
        wk = (iso[0], iso[1])
        if wk not in months[(cur.year, cur.month)]:
            months[(cur.year, cur.month)].append(wk)
        cur += timedelta(days=1)

    # For each month, compute consecutive losing weeks and mark all days in those weeks
    for ym, week_list in months.items():
        # Keep order as encountered
        streak_weeks: List[Tuple[int, int]] = []
        for wk in week_list:
            losing_week = month_weeks.get(wk, 0.0) < 0
            if losing_week:
                streak_weeks.append(wk)
            else:
                if len(streak_weeks) > max_losing_weeks_streak_month:
                    # mark days in these weeks
                    for k in list(days.keys()):
                        d = datetime.strptime(k, "%Y-%m-%d").date()
                        if d.isocalendar()[:2] in streak_weeks:
                            if "losing_weeks_month" not in days[k]["breaches"]:
                                days[k]["breaches"].append("losing_weeks_month")
                streak_weeks = []
        if len(streak_weeks) > max_losing_weeks_streak_month:
            for k in list(days.keys()):
                d = datetime.strptime(k, "%Y-%m-%d").date()
                if d.isocalendar()[:2] in streak_weeks:
                    if "losing_weeks_month" not in days[k]["breaches"]:
                        days[k]["breaches"].append("losing_weeks_month")

    # Risk cap exceeded badge (per day if any trade exceeded min cap)
    # Load playbook responses for trades in range (simple join by user)
    # Map trade_id -> (intended_risk_pct, template caps, grade schedule cap if grade present)
    # Prepare account caps map
    account_caps: Dict[int, Optional[float]] = {}
    for r in trades:
        if r.account_id not in account_caps:
            acc = db.query(Account).filter(Account.id == r.account_id).first()
            account_caps[r.account_id] = getattr(acc, 'account_max_risk_pct', None) if acc else None

    # Fetch responses and templates
    trade_ids = [r.id for r in trades if start_d <= event_local_day(r) <= end_d]
    if trade_ids:
        resp_rows = (
            db.query(PlaybookResponse, PlaybookTemplate)
            .join(PlaybookTemplate, PlaybookTemplate.id == PlaybookResponse.template_id)
            .filter(PlaybookResponse.user_id == current.id, PlaybookResponse.trade_id.in_(trade_ids))
            .all()
        )
        # Map trade_id to inferred exceeded flag by day
        exceeded_by_trade: Dict[int, bool] = {}
        for pr, tpl in resp_rows:
            intended = pr.intended_risk_pct
            if intended is None:
                continue
            template_max = tpl.template_max_risk_pct
            grade_cap = None
            if pr.computed_grade and tpl.risk_schedule_json:
                try:
                    sched = json.loads(tpl.risk_schedule_json)
                    grade_cap = float(sched.get(pr.computed_grade)) if sched.get(pr.computed_grade) is not None else None
                except Exception:
                    grade_cap = None
            acc_cap = account_caps.get(pr.trade_id and db.query(Trade.account_id).filter(Trade.id == pr.trade_id).scalar(), None)
            caps = [c for c in [template_max, grade_cap, acc_cap] if c is not None]
            if caps and float(intended) > min(caps):
                exceeded_by_trade[pr.trade_id] = True

        # Apply to days
        for r in trades:
            if r.id in exceeded_by_trade and exceeded_by_trade[r.id]:
                key = event_local_day(r).strftime("%Y-%m-%d")
                days.setdefault(key, {"date": key, "trades": 0, "net_pnl": 0.0, "breaches": []})
                if "risk_cap_exceeded" not in days[key]["breaches"]:
                    days[key]["breaches"].append("risk_cap_exceeded")

    # Sort days and round net_pnl
    result = []
    cur = start_d
    while cur <= end_d:
        key = cur.strftime("%Y-%m-%d")
        b = days.get(key, {"date": key, "trades": 0, "net_pnl": 0.0, "breaches": []})
        b["net_pnl"] = round(float(b["net_pnl"]), 2)
        result.append(b)
        cur += timedelta(days=1)

    return {"days": result}

@router.get("/forex-summary")
def get_forex_summary(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) inclusive"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) inclusive"),
):
    """
    Get forex-specific metrics:
    - Total pips won/lost
    - Average pips per trade
    - Win rate by pips (separate from $ win rate)
    - Average lot size
    - Best/worst pip trades
    - Total trades
    """
    # Build base query for forex trades
    query = (
        db.query(Trade)
        .join(Account, Account.id == Trade.account_id)
        .join(Instrument, Instrument.id == Trade.instrument_id)
        .filter(Account.user_id == current.id)
        .filter(Instrument.asset_class == 'forex')
    )

    # Apply filters
    if account_id:
        query = query.filter(Trade.account_id == account_id)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Trade.open_time_utc >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.filter(Trade.open_time_utc <= end_dt)
        except ValueError:
            pass

    trades = query.all()

    if not trades:
        return {
            "total_trades": 0,
            "total_pips": 0.0,
            "avg_pips_per_trade": 0.0,
            "pip_win_rate": 0.0,
            "avg_lot_size": 0.0,
            "best_pip_trade": 0.0,
            "worst_pip_trade": 0.0,
            "pip_winners": 0,
            "pip_losers": 0,
        }

    # Calculate metrics
    pip_values = [t.pips for t in trades if t.pips is not None]
    lot_sizes = [float(t.lot_size) for t in trades if t.lot_size is not None]

    total_pips = sum(pip_values) if pip_values else 0.0
    avg_pips = total_pips / len(pip_values) if pip_values else 0.0

    pip_winners = [p for p in pip_values if p > 0]
    pip_losers = [p for p in pip_values if p < 0]
    pip_win_rate = (len(pip_winners) / len(pip_values) * 100) if pip_values else 0.0

    return {
        "total_trades": len(trades),
        "total_pips": round(total_pips, 2),
        "avg_pips_per_trade": round(avg_pips, 2),
        "pip_win_rate": round(pip_win_rate, 2),
        "avg_lot_size": round(sum(lot_sizes) / len(lot_sizes), 2) if lot_sizes else 0.0,
        "best_pip_trade": round(max(pip_values), 2) if pip_values else 0.0,
        "worst_pip_trade": round(min(pip_values), 2) if pip_values else 0.0,
        "pip_winners": len(pip_winners),
        "pip_losers": len(pip_losers),
    }

@router.get("/futures-summary")
def get_futures_summary(
    db: Session = Depends(get_db),
    current = Depends(get_current_user),
    account_id: Optional[int] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) inclusive"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) inclusive"),
):
    """
    Get futures-specific metrics:
    - Total ticks won/lost
    - Average ticks per trade
    - Win rate by ticks (separate from $ win rate)
    - Average contracts traded
    - Best/worst tick trades
    - Total trades
    - Performance by contract (ES vs NQ, etc.)
    """
    # Build base query for futures trades
    query = (
        db.query(Trade, Instrument.symbol)
        .join(Account, Account.id == Trade.account_id)
        .join(Instrument, Instrument.id == Trade.instrument_id)
        .filter(Account.user_id == current.id)
        .filter(Instrument.asset_class == 'futures')
    )

    # Apply filters
    if account_id:
        query = query.filter(Trade.account_id == account_id)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Trade.open_time_utc >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.filter(Trade.open_time_utc <= end_dt)
        except ValueError:
            pass

    results = query.all()

    if not results:
        return {
            "total_trades": 0,
            "total_ticks": 0.0,
            "avg_ticks_per_trade": 0.0,
            "tick_win_rate": 0.0,
            "avg_contracts": 0.0,
            "best_tick_trade": 0.0,
            "worst_tick_trade": 0.0,
            "tick_winners": 0,
            "tick_losers": 0,
            "by_contract": {},
        }

    trades = [t for t, _ in results]
    
    # Calculate metrics
    tick_values = [t.ticks for t in trades if t.ticks is not None]
    contract_counts = [t.contracts for t in trades if t.contracts is not None]

    total_ticks = sum(tick_values) if tick_values else 0.0
    avg_ticks = total_ticks / len(tick_values) if tick_values else 0.0

    tick_winners = [t for t in tick_values if t > 0]
    tick_losers = [t for t in tick_values if t < 0]
    tick_win_rate = (len(tick_winners) / len(tick_values) * 100) if tick_values else 0.0

    # Group by contract root
    by_contract = {}
    for trade, symbol in results:
        if trade.ticks is None:
            continue
        # Extract root symbol (e.g., ES from ESH25)
        from app.futures_utils import parse_futures_symbol
        parsed = parse_futures_symbol(symbol)
        if parsed:
            root = parsed['root']
            if root not in by_contract:
                by_contract[root] = {
                    "trades": 0,
                    "total_ticks": 0.0,
                    "avg_ticks": 0.0,
                    "net_pnl": 0.0,
                }
            by_contract[root]["trades"] += 1
            by_contract[root]["total_ticks"] += trade.ticks
            by_contract[root]["net_pnl"] += trade.net_pnl or 0.0

    # Calculate averages
    for root in by_contract:
        if by_contract[root]["trades"] > 0:
            by_contract[root]["avg_ticks"] = round(by_contract[root]["total_ticks"] / by_contract[root]["trades"], 2)
        by_contract[root]["total_ticks"] = round(by_contract[root]["total_ticks"], 2)
        by_contract[root]["net_pnl"] = round(by_contract[root]["net_pnl"], 2)

    return {
        "total_trades": len(trades),
        "total_ticks": round(total_ticks, 2),
        "avg_ticks_per_trade": round(avg_ticks, 2),
        "tick_win_rate": round(tick_win_rate, 2),
        "avg_contracts": round(sum(contract_counts) / len(contract_counts), 2) if contract_counts else 0.0,
        "best_tick_trade": round(max(tick_values), 2) if tick_values else 0.0,
        "worst_tick_trade": round(min(tick_values), 2) if tick_values else 0.0,
        "tick_winners": len(tick_winners),
        "tick_losers": len(tick_losers),
        "by_contract": by_contract,
    }
