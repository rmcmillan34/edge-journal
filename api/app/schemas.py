from pydantic import BaseModel, EmailStr, Field, RootModel
from pydantic import ConfigDict
from typing import Dict, List, Optional
from typing import Any, Literal
from datetime import datetime
import warnings

# Suppress Pydantic warnings about 'schema' field shadowing BaseModel attribute
# This is intentional - we use 'schema' to describe playbook field definitions
warnings.filterwarnings('ignore', message='Field name "schema".*shadows an attribute', category=UserWarning)

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    tz: str

    # Pydantic v2 style config
    model_config = ConfigDict(from_attributes=True)

class MappingOverride(RootModel[Dict[str, str]]):
    """Root model wrapping a mapping of canonical field -> CSV header.

    Pydantic v2 requires RootModel for `__root__`-style models.
    """
    pass

class MappingPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    headers: List[str]
    mapping: Dict[str, str]

class MappingPresetOut(BaseModel):
    id: int
    name: str
    headers: List[str]
    mapping: Dict[str, str]


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    broker_label: Optional[str] = None
    base_ccy: Optional[str] = None

class AccountOut(BaseModel):
    id: int
    name: str
    broker_label: Optional[str] = None
    base_ccy: Optional[str] = None
    status: str
    account_max_risk_pct: Optional[float] = None
    closed_at: Optional[str] = None
    close_reason: Optional[str] = None
    close_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    broker_label: Optional[str] = None
    base_ccy: Optional[str] = None
    status: Optional[str] = None
    account_max_risk_pct: Optional[float] = None
    closed_at: Optional[str] = None
    close_reason: Optional[str] = None
    close_note: Optional[str] = None


class AccountClose(BaseModel):
    reason: Literal['breach', 'retired', 'merged', 'other'] = 'other'
    note: Optional[str] = None


class AccountReopen(BaseModel):
    note: Optional[str] = None


class TradeOut(BaseModel):
    id: int
    account_name: Optional[str]
    symbol: Optional[str]
    asset_class: Optional[str] = None  # forex/futures/equity
    side: str
    qty_units: Optional[float]
    entry_price: Optional[float]
    exit_price: Optional[float]
    open_time_utc: str
    close_time_utc: Optional[str]
    net_pnl: Optional[float]
    external_trade_id: Optional[str]

    # Forex-specific fields
    lot_size: Optional[float] = None
    pips: Optional[float] = None
    swap: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Futures-specific fields
    contracts: Optional[int] = None
    ticks: Optional[float] = None


class TradeCreate(BaseModel):
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    symbol: str
    side: str
    open_time: str
    close_time: Optional[str] = None
    qty_units: float
    entry_price: float
    exit_price: Optional[float] = None
    fees: Optional[float] = None
    net_pnl: Optional[float] = None
    notes_md: Optional[str] = None
    tz: Optional[str] = None

    # Forex-specific fields
    lot_size: Optional[float] = None
    pips: Optional[float] = None
    swap: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Futures-specific fields
    contracts: Optional[int] = None
    ticks: Optional[float] = None


class TradeUpdate(BaseModel):
    notes_md: Optional[str] = None
    fees: Optional[float] = None
    net_pnl: Optional[float] = None
    reviewed: Optional[bool] = None
    post_analysis_md: Optional[str] = None

    # Forex-specific fields
    lot_size: Optional[float] = None
    pips: Optional[float] = None
    swap: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Futures-specific fields
    contracts: Optional[int] = None
    ticks: Optional[float] = None


class AttachmentOut(BaseModel):
    id: int
    filename: str
    mime_type: Optional[str]
    size_bytes: Optional[int]
    timeframe: Optional[str]
    state: Optional[str]
    view: Optional[str]
    caption: Optional[str]
    reviewed: bool
    thumb_available: Optional[bool] = None
    thumb_url: Optional[str] = None
    sort_order: Optional[int] = None


class AttachmentUpdate(BaseModel):
    timeframe: Optional[str] = None
    state: Optional[str] = None
    view: Optional[str] = None
    caption: Optional[str] = None
    reviewed: Optional[bool] = None


class TradeDetailOut(TradeOut):
    notes_md: Optional[str]
    post_analysis_md: Optional[str]
    reviewed: bool
    attachments: list[AttachmentOut]

class UploadSummaryOut(BaseModel):
    id: int
    filename: str
    preset: Optional[str]
    status: str
    created_at: str
    inserted_count: int
    updated_count: int
    skipped_count: int
    error_count: int


# --- Daily Journal (M4) ---
class DailyJournalUpsert(BaseModel):
    title: Optional[str] = None
    notes_md: Optional[str] = None
    reviewed: Optional[bool] = None
    account_id: Optional[int] = None


class DailyJournalOut(BaseModel):
    id: int
    date: str
    title: Optional[str]
    notes_md: Optional[str]
    reviewed: bool
    account_id: Optional[int]
    trade_ids: List[int]


# --- Note Templates ---
class TemplateSection(BaseModel):
    heading: str
    default_included: bool = True
    placeholder: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str
    target: str  # 'trade' | 'daily'
    sections: List[TemplateSection]


class TemplateOut(BaseModel):
    id: int
    name: str
    target: str
    sections: List[TemplateSection]
    created_at: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    sections: Optional[List[TemplateSection]] = None


# --- Playbooks (M5) ---
class PlaybookField(BaseModel):
    key: str
    label: str
    type: Literal['boolean','select','number','text','rating','rich_text']
    required: Optional[bool] = False
    weight: Optional[float] = 1.0
    allow_comment: Optional[bool] = False
    validation: Optional[Dict[str, Any]] = None  # {min,max,regex,options[]}
    rich_text: Optional[bool] = None


class PlaybookTemplateCreate(BaseModel):
    name: str
    purpose: Literal['pre','in','post','generic']
    strategy_bindings: Optional[List[str]] = None
    schema: List[PlaybookField]
    grade_thresholds: Optional[Dict[str, float]] = None
    risk_schedule: Optional[Dict[str, float]] = None
    template_max_risk_pct: Optional[float] = None


class PlaybookTemplateOut(BaseModel):
    id: int
    name: str
    purpose: str
    version: int
    is_active: bool
    schema: List[PlaybookField]
    grade_thresholds: Optional[Dict[str, float]] = None
    risk_schedule: Optional[Dict[str, float]] = None
    template_max_risk_pct: Optional[float] = None
    created_at: Optional[str] = None


class PlaybookTemplateUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[Literal['pre','in','post','generic']] = None
    strategy_bindings: Optional[List[str]] = None
    schema: Optional[List[PlaybookField]] = None
    grade_thresholds: Optional[Dict[str, float]] = None
    risk_schedule: Optional[Dict[str, float]] = None
    template_max_risk_pct: Optional[float] = None


class PlaybookTemplateMeta(BaseModel):
    id: int
    name: str
    purpose: str
    version: int


class PlaybookResponseCreate(BaseModel):
    template_id: int
    template_version: Optional[int] = None
    values: Dict[str, Any]
    comments: Optional[Dict[str, str]] = None
    intended_risk_pct: Optional[float] = None


class PlaybookResponseOut(BaseModel):
    id: int
    template_id: int
    template_version: int
    values: Dict[str, Any]
    comments: Optional[Dict[str, str]] = None
    computed_grade: Optional[str] = None
    compliance_score: Optional[float] = None
    intended_risk_pct: Optional[float] = None
    created_at: Optional[str] = None
    template_meta: Optional[PlaybookTemplateMeta] = None
    warning: Optional[str] = None  # M6: enforcement mode warnings


class EvidenceCreate(BaseModel):
    field_key: str
    source_kind: Literal['trade','journal','url']
    source_id: Optional[int] = None
    url: Optional[str] = None
    note: Optional[str] = None


class EvidenceOut(BaseModel):
    id: int
    field_key: str
    source_kind: str
    source_id: Optional[int] = None
    url: Optional[str] = None
    note: Optional[str] = None


class TradingRules(BaseModel):
    max_losses_row_day: int
    max_losing_days_streak_week: int
    max_losing_weeks_streak_month: int
    alerts_enabled: bool = True
    enforcement_mode: Optional[Literal['off','warn','block']] = 'off'


class PlaybookEvaluateIn(BaseModel):
    template_id: Optional[int] = None
    schema: Optional[List[PlaybookField]] = None
    values: Dict[str, Any]
    grade_thresholds: Optional[Dict[str, float]] = None
    risk_schedule: Optional[Dict[str, float]] = None
    template_max_risk_pct: Optional[float] = None
    account_max_risk_pct: Optional[float] = None
    intended_risk_pct: Optional[float] = None


class PlaybookEvaluateOut(BaseModel):
    compliance_score: float
    grade: Literal['A','B','C','D']
    risk_cap_pct: float
    cap_breakdown: Dict[str, Optional[float]]
    exceeded: Optional[bool] = None
    messages: Optional[List[str]] = None


class PlaybookTemplateCloneIn(BaseModel):
    name: Optional[str] = None
    purpose: Optional[Literal['pre','in','post','generic']] = None


# --- Breach Events (M6 alerting) ---
class BreachEventOut(BaseModel):
    id: int
    scope: Literal['day','week','month','trade']
    date_or_week: str
    rule_key: str
    details: Optional[Dict[str, Any]] = None
    acknowledged: Optional[bool] = None
    created_at: Optional[str] = None


# --- Filter Builder (M7) ---
FilterOperator = Literal[
    'eq',        # equals
    'ne',        # not equals
    'contains',  # string contains (case-insensitive)
    'in',        # value in list
    'not_in',    # value not in list
    'gte',       # ≥
    'lte',       # ≤
    'gt',        # >
    'lt',        # <
    'between',   # date/number range
    'is_null',   # field is NULL
    'not_null'   # field is NOT NULL
]


class Condition(BaseModel):
    """Single filter condition"""
    field: str
    op: FilterOperator
    value: Optional[Any] = None  # Can be string, number, list, or None for null checks


class Filter(BaseModel):
    """Recursive filter group with AND/OR operator"""
    operator: Literal['AND', 'OR']
    conditions: List[Any]  # List of Condition or Filter (recursive)

    model_config = ConfigDict(arbitrary_types_allowed=True)


# --- Saved Views (M7) ---
class SavedViewCreate(BaseModel):
    """Schema for creating a saved view"""
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    filters_json: str = Field(..., description="Filter DSL as JSON string")
    columns_json: Optional[str] = None
    sort_json: Optional[str] = None
    group_by: Optional[str] = None
    is_default: bool = False


class SavedViewUpdate(BaseModel):
    """Schema for updating a saved view"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    filters_json: Optional[str] = None
    columns_json: Optional[str] = None
    sort_json: Optional[str] = None
    group_by: Optional[str] = None
    is_default: Optional[bool] = None


class SavedViewOut(BaseModel):
    """Schema for saved view response"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    filters_json: str
    columns_json: Optional[str]
    sort_json: Optional[str]
    group_by: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Reports (M7 Phase 3) ---
class ReportPeriod(BaseModel):
    """Period specification for reports"""
    year: Optional[int] = None
    month: Optional[int] = None
    week: Optional[int] = None
    date: Optional[str] = None  # YYYY-MM-DD for daily reports
    trade_id: Optional[int] = None  # For single trade reports


class ReportGenerateRequest(BaseModel):
    """Request schema for report generation"""
    type: Literal["trade", "daily", "weekly", "monthly", "yearly", "ytd", "alltime"]
    period: ReportPeriod
    view_id: Optional[int] = None
    account_ids: Optional[List[int]] = None  # If None, includes all accounts
    account_separation_mode: Literal["combined", "grouped", "separate"] = "combined"
    theme: Literal["light", "dark"] = "light"
    include_screenshots: bool = True


class ReportHistoryOut(BaseModel):
    """Report history item"""
    id: int
    filename: str
    report_type: str
    created_at: datetime
    file_size_bytes: int

    model_config = ConfigDict(from_attributes=True)
