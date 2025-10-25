from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .deps import get_current_user
from .db import get_db
from .models import User, UserTradingRules
from .schemas import TradingRules

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/trading-rules", response_model=TradingRules)
def get_trading_rules(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    row = db.query(UserTradingRules).filter(UserTradingRules.user_id == current.id).first()
    if not row:
        # Defaults
        return TradingRules(max_losses_row_day=3, max_losing_days_streak_week=2, max_losing_weeks_streak_month=2, alerts_enabled=True, enforcement_mode='off')
    return TradingRules(
        max_losses_row_day=row.max_losses_row_day,
        max_losing_days_streak_week=row.max_losing_days_streak_week,
        max_losing_weeks_streak_month=row.max_losing_weeks_streak_month,
        alerts_enabled=row.alerts_enabled,
        enforcement_mode=row.enforcement_mode or 'off',
    )


@router.put("/trading-rules", response_model=TradingRules)
def put_trading_rules(body: TradingRules, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    row = db.query(UserTradingRules).filter(UserTradingRules.user_id == current.id).first()
    if not row:
        row = UserTradingRules(
            user_id=current.id,
            max_losses_row_day=body.max_losses_row_day,
            max_losing_days_streak_week=body.max_losing_days_streak_week,
            max_losing_weeks_streak_month=body.max_losing_weeks_streak_month,
            alerts_enabled=body.alerts_enabled,
            enforcement_mode=body.enforcement_mode or 'off',
        )
        db.add(row)
    else:
        row.max_losses_row_day = body.max_losses_row_day
        row.max_losing_days_streak_week = body.max_losing_days_streak_week
        row.max_losing_weeks_streak_month = body.max_losing_weeks_streak_month
        row.alerts_enabled = body.alerts_enabled
        row.enforcement_mode = body.enforcement_mode or 'off'
    db.commit()
    return body
