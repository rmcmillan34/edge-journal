from pydantic import BaseModel, EmailStr, Field, RootModel
from pydantic import ConfigDict
from typing import Dict, List, Optional

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

    model_config = ConfigDict(from_attributes=True)


class TradeOut(BaseModel):
    id: int
    account_name: Optional[str]
    symbol: Optional[str]
    side: str
    qty_units: Optional[float]
    entry_price: Optional[float]
    exit_price: Optional[float]
    open_time_utc: str
    close_time_utc: Optional[str]
    net_pnl: Optional[float]
    external_trade_id: Optional[str]


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


class TradeUpdate(BaseModel):
    notes_md: Optional[str] = None
    fees: Optional[float] = None
    net_pnl: Optional[float] = None
    reviewed: Optional[bool] = None
    post_analysis_md: Optional[str] = None


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
