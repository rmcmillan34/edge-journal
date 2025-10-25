"""
M6 Guardrails Enforcement Logic

Provides enforcement mode checking ('off'|'warn'|'block') for:
- Risk cap violations (playbook responses)
- Loss streak violations (trade creation)
"""

from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from .models import UserTradingRules, BreachEvent, Trade, Account


def get_user_enforcement_mode(db: Session, user_id: int) -> str:
    """Get user's enforcement mode setting, default 'off'"""
    rules = db.query(UserTradingRules).filter(UserTradingRules.user_id == user_id).first()
    if not rules:
        return 'off'
    return rules.enforcement_mode or 'off'


def check_risk_cap_breach(
    db: Session,
    user_id: int,
    account_id: Optional[int],
    intended_risk_pct: float,
    min_cap: float,
    details: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Check if intended risk exceeds minimum cap.

    Returns:
        (is_breach, warning_message)

    Behavior by enforcement_mode:
        - 'off': logs breach, returns (True, None) - no warning to user
        - 'warn': logs breach, returns (True, warning) - warn user
        - 'block': logs breach, raises HTTPException 403
    """
    from fastapi import HTTPException

    if intended_risk_pct <= min_cap:
        return (False, None)

    enforcement_mode = get_user_enforcement_mode(db, user_id)

    # ALWAYS log breach event regardless of enforcement mode
    day_key = details.get('date_key', '')
    be = BreachEvent(
        user_id=user_id,
        account_id=account_id,
        scope='trade',
        date_or_week=day_key,
        rule_key='risk_cap_exceeded',
        details_json=json.dumps(details),
    )
    db.add(be)
    try:
        db.commit()
    except Exception:
        db.rollback()

    # If 'off' mode, log but don't warn or block
    if enforcement_mode == 'off':
        return (True, None)

    # Construct warning message
    warning = (
        f"Risk cap breach: intended {intended_risk_pct:.2f}% exceeds "
        f"cap of {min_cap:.2f}% (grade: {details.get('grade', 'N/A')})"
    )

    if enforcement_mode == 'block':
        raise HTTPException(
            status_code=403,
            detail={
                "error": "RISK_CAP_EXCEEDED",
                "message": warning,
                "intended_risk_pct": intended_risk_pct,
                "cap": min_cap,
                "enforcement_mode": "block"
            }
        )

    # 'warn' mode
    return (True, warning)


def check_loss_streaks(
    db: Session,
    user_id: int,
    account_id: int,
    trade_close_date: datetime
) -> Tuple[List[str], List[str]]:
    """
    Check if trade would violate daily/weekly/monthly loss streak rules.

    Returns:
        (breaches, warnings)

    breaches: list of rule_key strings ('loss_streak_day', 'losing_days_week', 'losing_weeks_month')
    warnings: list of warning messages

    Behavior by enforcement_mode:
        - 'off': returns ([], [])
        - 'warn': returns (breaches, warnings) and logs breaches
        - 'block': raises HTTPException 403 on first breach
    """
    from fastapi import HTTPException

    enforcement_mode = get_user_enforcement_mode(db, user_id)

    if enforcement_mode == 'off':
        return ([], [])

    rules = db.query(UserTradingRules).filter(UserTradingRules.user_id == user_id).first()
    if not rules:
        return ([], [])

    breaches: List[str] = []
    warnings: List[str] = []

    # Check daily loss streak
    if rules.max_losses_row_day and rules.max_losses_row_day > 0:
        day_str = trade_close_date.date().isoformat()
        # Count consecutive losing trades on this day
        day_trades = (
            db.query(Trade)
            .filter(
                Trade.account_id == account_id,
                Trade.close_time_utc >= datetime.fromisoformat(day_str).replace(tzinfo=timezone.utc),
                Trade.close_time_utc < datetime.fromisoformat(day_str).replace(tzinfo=timezone.utc).replace(hour=23, minute=59, second=59),
                Trade.net_pnl < 0
            )
            .order_by(Trade.close_time_utc.asc())
            .all()
        )

        # Count consecutive losses
        consecutive_losses = 0
        for t in day_trades:
            if t.net_pnl and t.net_pnl < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0

        if consecutive_losses >= rules.max_losses_row_day:
            breaches.append('loss_streak_day')
            warning = f"Daily loss streak: {consecutive_losses} consecutive losses (max: {rules.max_losses_row_day})"
            warnings.append(warning)

            # Log breach
            be = BreachEvent(
                user_id=user_id,
                account_id=account_id,
                scope='day',
                date_or_week=day_str,
                rule_key='loss_streak_day',
                details_json=json.dumps({"consecutive_losses": consecutive_losses, "max": rules.max_losses_row_day}),
            )
            db.add(be)

            if enforcement_mode == 'block':
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "LOSS_STREAK_EXCEEDED",
                        "message": warning,
                        "rule": "max_losses_row_day",
                        "consecutive_losses": consecutive_losses,
                        "max_allowed": rules.max_losses_row_day,
                        "enforcement_mode": "block"
                    }
                )

    # Commit breach logs for warn mode
    if breaches and enforcement_mode == 'warn':
        try:
            db.commit()
        except Exception:
            db.rollback()

    return (breaches, warnings)
