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
