from sqlalchemy import Column, Integer, String, DateTime, func, Boolean, ForeignKey, UniqueConstraint, Float, Text
from sqlalchemy.orm import relationship
from .db import Base

class User(Base):
    """
    User model for storing user information.

    Attributes:
        id (int): Primary key.
        email (str): User's email address, unique.
        password_hash (str): Hashed password for authentication.
        is_active (bool): Status of the user account.
        tz (str): User's timezone, default is "Australia/Sydney".
        created_at (datetime): Timestamp of account creation.
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    tz = Column(String(64), default="Australia/Sydney", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# --- Uploads (to audit imports) ---
class Upload(Base):
    """
    Upload model for tracking file uploads.

    Attributes:
        id (int): Primary key.
        filename (str): Name of the uploaded file.
        preset (str): Optional preset used during upload.
        file_hash (str): Optional hash of the file for idempotency.
        status (str): Status of the upload, either "committed" or "dry-run".
        created_at (datetime): Timestamp of when the upload was created.
    """
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    preset = Column(String(64), nullable=True)
    file_hash = Column(String(64), nullable=True)  # optional, for idempotency later
    status = Column(String(32), nullable=False, default="committed")  # or "dry-run"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    inserted_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    errors_json = Column(Text, nullable=True)
    tz = Column(String(64), nullable=True)


# --- Minimal stubs (real fields later) ---
class Account(Base):
    """
    Account model for storing trading account information.
    
    Attributes:
        id (int): Primary key.
        name (str): Name of the account.
        broker_label (str): Optional label for the broker.
        base_ccy (str): Optional base currency of the account.
        status (str): Status of the account, either "active" or "closed".
    """
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True, index=True)
    name = Column(String(120), nullable=False)
    broker_label = Column(String(120), nullable=True)
    base_ccy = Column(String(12), nullable=True)
    status = Column(String(16), nullable=False, default="active")  # active/closed


class Instrument(Base):
    """
    Instrument model for storing financial instrument information.
    Attributes:
        id (int): Primary key.
        symbol (str): Unique symbol of the instrument.
        asset_class (str): Optional asset class, e.g., forex or futures.
    """
    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(64), unique=True, nullable=False)
    asset_class = Column(String(16), nullable=True)  # forex/futures (later)


# --- Trades (normalized, minimal for MVP) ---
class Trade(Base):
    """
    Trade model for storing trading information.

    Attributes:
        id (int): Primary key.
        account_id (int): Foreign key to the Account model.
        instrument_id (int): Foreign key to the Instrument model.
        external_trade_id (str): Optional external trade identifier.
        side (str): Side of the trade, either "Buy" or "Sell".
        qty_units (float): Quantity of units traded.
        entry_price (float): Entry price of the trade.
        exit_price (float): Exit price of the trade.
        open_time_utc (datetime): UTC timestamp of when the trade was opened.
        close_time_utc (datetime): UTC timestamp of when the trade was closed.
        gross_pnl (float): Gross profit and loss of the trade.
        fees (float): Fees associated with the trade.
        net_pnl (float): Net profit and loss of the trade.
        notes_md (str): Optional markdown notes about the trade.
        source_upload_id (int): Foreign key to the Upload model indicating the source of the trade.
        trade_key (str): Unique key for deduplication of trades.
        version (int): Version number for tracking updates to the trade.
    """
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)

    external_trade_id = Column(String(128), nullable=True)
    side = Column(String(8), nullable=False)  # Buy/Sell
    qty_units = Column(Float, nullable=True)

    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)

    open_time_utc = Column(DateTime(timezone=True), nullable=False)
    close_time_utc = Column(DateTime(timezone=True), nullable=True)

    gross_pnl = Column(Float, nullable=True)
    fees = Column(Float, nullable=True)
    net_pnl = Column(Float, nullable=True)

    notes_md = Column(String, nullable=True)
    source_upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=True)

    trade_key = Column(String(256), nullable=False)  # dedupe key
    version = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("trade_key", name="uq_trades_tradekey"),
    )


class MappingPreset(Base):
    __tablename__ = "mapping_presets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    headers_json = Column(Text, nullable=False)
    mapping_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_mapping_presets_user_name"),)
