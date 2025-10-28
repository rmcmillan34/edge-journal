# M8: Forex & Futures - Technical Design

**Status:** Draft
**Version:** 0.1.0
**Target Release:** v0.8.0

## Overview

M8 adds support for forex and futures trading to Edge-Journal. Currently the system is asset-class agnostic, treating all trades generically. This milestone adds:

1. Asset class differentiation (forex/futures/equity)
2. Forex-specific features (pips, lot sizes, swaps, SL/TP tracking)
3. Futures-specific features (contract specs, expiration, tick-based metrics)
4. Enhanced CSV import for forex/futures broker formats
5. Asset-class-aware UI and metrics

**Migration Note:** Based on user's current usage, existing trades will be migrated to `asset_class='forex'`.

---

## Phase 1: Foundation - Asset Class Support

### 1.1 Database Changes

**Update Instrument model:**
```python
class Instrument(Base):
    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(64), unique=True, nullable=False)
    asset_class = Column(String(16), nullable=False, default='forex')  # forex/futures/equity
    # New fields for forex:
    pip_location = Column(Integer, nullable=True)  # 10, 100, 10000 (for JPY pairs, most pairs, gold/indices)
    # New fields for futures:
    contract_size = Column(Integer, nullable=True)  # e.g., 50 for ES, 20 for CL
    tick_size = Column(Numeric(10,6), nullable=True)  # e.g., 0.25 for ES
    tick_value = Column(Numeric(10,2), nullable=True)  # e.g., 12.50 for ES
    expiration_date = Column(Date, nullable=True)  # for futures contracts
    contract_month = Column(String(16), nullable=True)  # e.g., "MAR2025", "H25"
```

**Update Trade model to add forex/futures-specific fields:**
```python
class Trade(Base):
    __tablename__ = "trades"
    # ... existing fields ...

    # Forex-specific:
    lot_size = Column(Numeric(10,2), nullable=True)  # 1.0, 0.1, 0.01 (standard, mini, micro)
    pips = Column(Numeric(10,2), nullable=True)  # calculated pip P&L
    swap = Column(Numeric(10,2), nullable=True)  # overnight interest (separate from fees)
    stop_loss = Column(Numeric(12,6), nullable=True)  # SL price level
    take_profit = Column(Numeric(12,6), nullable=True)  # TP price level

    # Futures-specific:
    contracts = Column(Integer, nullable=True)  # number of contracts
    ticks = Column(Numeric(10,2), nullable=True)  # tick-based P&L
```

**Migration script (0018_forex_futures_support.py):**
```python
def upgrade():
    # Add new columns to instruments
    op.add_column('instruments', sa.Column('pip_location', sa.Integer(), nullable=True))
    op.add_column('instruments', sa.Column('contract_size', sa.Integer(), nullable=True))
    op.add_column('instruments', sa.Column('tick_size', sa.Numeric(10,6), nullable=True))
    op.add_column('instruments', sa.Column('tick_value', sa.Numeric(10,2), nullable=True))
    op.add_column('instruments', sa.Column('expiration_date', sa.Date(), nullable=True))
    op.add_column('instruments', sa.Column('contract_month', sa.String(16), nullable=True))

    # Change asset_class to NOT NULL with default
    op.alter_column('instruments', 'asset_class',
                    existing_type=sa.String(16),
                    nullable=False,
                    server_default='forex')

    # Migrate existing instruments to forex
    op.execute("UPDATE instruments SET asset_class = 'forex' WHERE asset_class IS NULL OR asset_class = ''")

    # Add new columns to trades
    op.add_column('trades', sa.Column('lot_size', sa.Numeric(10,2), nullable=True))
    op.add_column('trades', sa.Column('pips', sa.Numeric(10,2), nullable=True))
    op.add_column('trades', sa.Column('swap', sa.Numeric(10,2), nullable=True))
    op.add_column('trades', sa.Column('stop_loss', sa.Numeric(12,6), nullable=True))
    op.add_column('trades', sa.Column('take_profit', sa.Numeric(12,6), nullable=True))
    op.add_column('trades', sa.Column('contracts', sa.Integer(), nullable=True))
    op.add_column('trades', sa.Column('ticks', sa.Numeric(10,2), nullable=True))
```

### 1.2 Backend API Updates

**schemas.py - Add forex/futures fields to Trade schemas:**
```python
class TradeOut(BaseModel):
    # ... existing fields ...

    # Forex fields
    lot_size: float | None = None
    pips: float | None = None
    swap: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None

    # Futures fields
    contracts: int | None = None
    ticks: float | None = None

    # From joined instrument
    asset_class: str | None = None
```

**Update routes_trades.py to return asset_class:**
```python
# Join with instrument to get asset_class
query = db.query(Trade, Instrument.symbol, Instrument.asset_class, Account.name).join(...)
```

**Add routes_instruments.py for instrument metadata management:**
```python
@router.get("/instruments", response_model=List[InstrumentOut])
def list_instruments(asset_class: str | None = None, ...):
    """List instruments with optional filtering by asset_class"""

@router.get("/instruments/{symbol}", response_model=InstrumentDetailOut)
def get_instrument(symbol: str, ...):
    """Get detailed instrument info including metadata"""

@router.patch("/instruments/{symbol}", response_model=InstrumentOut)
def update_instrument(symbol: str, body: InstrumentUpdate, ...):
    """Update instrument metadata (pip_location, contract_size, etc.)"""
```

### 1.3 UI Updates

**Add asset class badge on trade list and detail pages:**
```tsx
// components/AssetClassBadge.tsx
export function AssetClassBadge({ assetClass }: { assetClass: string }) {
  const colors = {
    forex: 'bg-blue-500/20 text-blue-300',
    futures: 'bg-purple-500/20 text-purple-300',
    equity: 'bg-green-500/20 text-green-300',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[assetClass]}`}>
      {assetClass.toUpperCase()}
    </span>
  );
}
```

**Update trade list table headers:**
- Quantity → "Lots" for forex, "Contracts" for futures, "Shares" for equity

**Add helper to determine quantity label:**
```tsx
// utils/assetClass.ts
export function getQuantityLabel(assetClass: string): string {
  switch (assetClass) {
    case 'forex': return 'Lots';
    case 'futures': return 'Contracts';
    case 'equity': return 'Shares';
    default: return 'Quantity';
  }
}
```

---

## Phase 2: Forex Support

### 2.1 Forex Utilities

**Create forex_utils.py:**
```python
def calculate_pips(symbol: str, entry_price: float, exit_price: float, side: str, pip_location: int = None) -> float:
    """
    Calculate pip difference for a forex trade.

    Args:
        symbol: Currency pair (e.g., EURUSD, GBPJPY)
        entry_price: Entry price
        exit_price: Exit price
        side: 'buy' or 'sell'
        pip_location: Override pip location (10 for JPY pairs, 10000 for most pairs)

    Returns:
        Pip value (positive for profit, negative for loss)
    """
    if pip_location is None:
        pip_location = detect_pip_location(symbol)

    price_diff = exit_price - entry_price
    if side.lower() == 'sell':
        price_diff = -price_diff

    pips = price_diff * pip_location
    return round(pips, 2)

def detect_pip_location(symbol: str) -> int:
    """
    Detect pip location based on currency pair.

    Returns:
        10 for JPY pairs (0.01 = 1 pip)
        10000 for most pairs (0.0001 = 1 pip)
        100 for exotic pairs and metals
    """
    if 'JPY' in symbol.upper():
        return 10
    elif any(x in symbol.upper() for x in ['XAU', 'XAG', 'GOLD', 'SILVER']):
        return 100
    else:
        return 10000

def calculate_lot_value(symbol: str, lot_size: float, price: float) -> float:
    """Calculate notional value of a forex position."""
    # 1 standard lot = 100,000 units of base currency
    standard_lot_units = 100000
    units = lot_size * standard_lot_units
    return units * price

def infer_lot_size_from_qty(qty_units: float, symbol: str) -> float:
    """
    Infer lot size from quantity units.
    E.g., 100000 units = 1.0 lot, 10000 units = 0.1 lot
    """
    if qty_units is None:
        return None
    standard_lot_units = 100000
    return round(qty_units / standard_lot_units, 2)
```

### 2.2 CSV Import Enhancements

**Update routes_uploads.py to handle forex-specific fields:**

**FTMO Format Mapping (primary focus):**
```python
# Required canonical fields (keep existing):
"Account", "Symbol", "Side", "Open Time", "Quantity", "Entry Price"

# New optional forex fields:
"Lot Size"      # Volume from FTMO CSV
"Pips"          # Pips from FTMO CSV (pre-calculated)
"Swap"          # Swap from FTMO CSV (overnight interest)
"Stop Loss"     # SL from FTMO CSV
"Take Profit"   # TP from FTMO CSV
```

**Update commit logic in routes_uploads.py:**
```python
# After creating/finding instrument:
instrument = get_or_create_instrument(db, symbol_str, user_id=current.id)

# Set asset_class if symbol looks like forex pair
if '/' in symbol_str or is_forex_pair(symbol_str):
    if not instrument.asset_class:
        instrument.asset_class = 'forex'
        instrument.pip_location = detect_pip_location(symbol_str)
        db.add(instrument)

# Extract forex-specific fields from row
lot_size_direct = safe_float(row_dict.get(mapping.get("Lot Size"))) or safe_float(row_dict.get(mapping.get("Volume")))
pips = safe_float(row_dict.get(mapping.get("Pips")))
swap = safe_float(row_dict.get(mapping.get("Swap")))
stop_loss = safe_float(row_dict.get(mapping.get("Stop Loss")))
take_profit = safe_float(row_dict.get(mapping.get("Take Profit")))

# Smart fallback for lot size: calculate from qty_units if not provided
if lot_size_direct is None and qty_units and instrument.asset_class == 'forex':
    lot_size = infer_lot_size_from_qty(qty_units, symbol_str)
else:
    lot_size = lot_size_direct

# Calculate pips if not provided
if pips is None and instrument.asset_class == 'forex' and entry_price and exit_price:
    pips = calculate_pips(symbol_str, entry_price, exit_price, side, instrument.pip_location)

# Create trade with forex fields
trade = Trade(
    # ... existing fields ...
    lot_size=lot_size,
    pips=pips,
    swap=swap,
    stop_loss=stop_loss,
    take_profit=take_profit,
)
```

**Add is_forex_pair helper:**
```python
def is_forex_pair(symbol: str) -> bool:
    """Detect if symbol is likely a forex pair."""
    symbol_upper = symbol.upper().replace('/', '')
    forex_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD'}

    # Check if it's exactly 6 chars and both halves are known currencies
    if len(symbol_upper) == 6:
        base = symbol_upper[:3]
        quote = symbol_upper[3:]
        return base in forex_currencies and quote in forex_currencies

    return False
```

### 2.3 Forex-Specific Metrics

**Add to routes_metrics.py:**
```python
@router.get("/metrics/forex-summary")
def get_forex_summary(
    account_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    """
    Get forex-specific metrics:
    - Total pips won/lost
    - Average pips per trade
    - Win rate by pips (separate from $ win rate)
    - Average lot size
    - Best/worst pip trades
    - Pip P&L by symbol
    """
    query = db.query(Trade).filter(Trade.user_id == current.id)
    # Join instrument to filter by asset_class='forex'
    query = query.join(Instrument).filter(Instrument.asset_class == 'forex')

    # Apply filters...

    trades = query.all()

    total_pips = sum(t.pips for t in trades if t.pips is not None)
    avg_pips = total_pips / len(trades) if trades else 0
    pip_winners = [t for t in trades if t.pips and t.pips > 0]
    pip_win_rate = len(pip_winners) / len(trades) * 100 if trades else 0

    return {
        "total_pips": round(total_pips, 2),
        "avg_pips_per_trade": round(avg_pips, 2),
        "pip_win_rate": round(pip_win_rate, 2),
        "avg_lot_size": round(sum(t.lot_size for t in trades if t.lot_size) / len(trades), 2),
        "best_pip_trade": max((t.pips for t in trades if t.pips), default=0),
        "worst_pip_trade": min((t.pips for t in trades if t.pips), default=0),
    }
```

### 2.4 UI Enhancements

**Trade detail page (app/trades/[id]/page.tsx):**
```tsx
{trade.asset_class === 'forex' && (
  <div className="forex-details">
    <div className="stat-row">
      <span className="label">Lot Size:</span>
      <span className="value">{trade.lot_size} lots</span>
    </div>
    <div className="stat-row">
      <span className="label">Pips:</span>
      <span className={`value ${trade.pips >= 0 ? 'text-green-400' : 'text-red-400'}`}>
        {trade.pips >= 0 ? '+' : ''}{trade.pips} pips
      </span>
    </div>
    {trade.swap && (
      <div className="stat-row">
        <span className="label">Swap:</span>
        <span className="value">${trade.swap.toFixed(2)}</span>
      </div>
    )}
    {trade.stop_loss && (
      <div className="stat-row">
        <span className="label">Stop Loss:</span>
        <span className="value">{trade.stop_loss}</span>
      </div>
    )}
    {trade.take_profit && (
      <div className="stat-row">
        <span className="label">Take Profit:</span>
        <span className="value">{trade.take_profit}</span>
      </div>
    )}
  </div>
)}
```

**Dashboard KPIs (app/dashboard/page.tsx):**
```tsx
// Add forex-specific KPI tile when viewing forex trades
{selectedAssetClass === 'forex' && (
  <div className="kpi-tile">
    <div className="kpi-label">Total Pips</div>
    <div className={`kpi-value ${forexMetrics.total_pips >= 0 ? 'text-green-400' : 'text-red-400'}`}>
      {forexMetrics.total_pips >= 0 ? '+' : ''}{forexMetrics.total_pips}
    </div>
    <div className="kpi-sublabel">Avg: {forexMetrics.avg_pips_per_trade} pips/trade</div>
  </div>
)}
```

**Add asset class filter to trades list and dashboard:**
```tsx
<select value={assetClassFilter} onChange={(e) => setAssetClassFilter(e.target.value)}>
  <option value="">All Asset Classes</option>
  <option value="forex">Forex</option>
  <option value="futures">Futures</option>
  <option value="equity">Equity</option>
</select>
```

---

## Phase 3: Futures Support

### 3.1 Futures Utilities

**Create futures_utils.py:**
```python
def parse_futures_symbol(symbol: str) -> dict:
    """
    Parse futures symbol to extract root, month, year.

    Examples:
        ESH25 → {'root': 'ES', 'month_code': 'H', 'year': '25', 'month': 'MAR', 'full_year': 2025}
        NQM2024 → {'root': 'NQ', 'month_code': 'M', 'year': '2024', 'month': 'JUN', 'full_year': 2024}
    """
    MONTH_CODES = {
        'F': 'JAN', 'G': 'FEB', 'H': 'MAR', 'J': 'APR', 'K': 'MAY', 'M': 'JUN',
        'N': 'JUL', 'Q': 'AUG', 'U': 'SEP', 'V': 'OCT', 'X': 'NOV', 'Z': 'DEC'
    }

    # Match patterns like ESH25, NQM2024
    import re
    match = re.match(r'^([A-Z]{1,4})([FGHJKMNQUVXZ])(\d{2,4})$', symbol.upper())
    if not match:
        return None

    root, month_code, year_str = match.groups()

    # Handle 2-digit or 4-digit year
    if len(year_str) == 2:
        full_year = 2000 + int(year_str)
    else:
        full_year = int(year_str)

    return {
        'root': root,
        'month_code': month_code,
        'month': MONTH_CODES[month_code],
        'year': year_str,
        'full_year': full_year,
    }

def calculate_ticks(entry_price: float, exit_price: float, side: str, tick_size: float) -> float:
    """Calculate tick-based P&L for futures."""
    price_diff = exit_price - entry_price
    if side.lower() == 'sell':
        price_diff = -price_diff

    ticks = price_diff / tick_size
    return round(ticks, 2)

def get_contract_specs(root: str) -> dict:
    """
    Return contract specifications for common futures.

    This would ideally be stored in the database or external config.
    """
    specs = {
        'ES': {'name': 'E-mini S&P 500', 'contract_size': 50, 'tick_size': 0.25, 'tick_value': 12.50},
        'NQ': {'name': 'E-mini Nasdaq', 'contract_size': 20, 'tick_size': 0.25, 'tick_value': 5.00},
        'YM': {'name': 'E-mini Dow', 'contract_size': 5, 'tick_size': 1.0, 'tick_value': 5.00},
        'CL': {'name': 'Crude Oil', 'contract_size': 1000, 'tick_size': 0.01, 'tick_value': 10.00},
        'GC': {'name': 'Gold', 'contract_size': 100, 'tick_size': 0.10, 'tick_value': 10.00},
        'MES': {'name': 'Micro E-mini S&P', 'contract_size': 5, 'tick_size': 0.25, 'tick_value': 1.25},
        'MNQ': {'name': 'Micro E-mini Nasdaq', 'contract_size': 2, 'tick_size': 0.25, 'tick_value': 0.50},
    }
    return specs.get(root.upper())
```

### 3.2 CSV Import for Futures

**Add futures broker format support (Tradovate, ThinkorSwim, NinjaTrader):**
```python
# New optional futures fields:
"Contract"       # Contract symbol (e.g., ESH25)
"Expiration"     # Expiration date
"Contracts"      # Number of contracts (instead of Quantity/Lot Size)
"Ticks"          # Pre-calculated tick P&L
"Tick Size"      # Override tick size
```

**Update commit logic:**
```python
# Auto-detect futures symbol
parsed = parse_futures_symbol(symbol_str)
if parsed:
    # This is a futures contract
    instrument.asset_class = 'futures'
    instrument.contract_month = f"{parsed['month']}{parsed['full_year']}"

    # Get contract specs and populate metadata
    specs = get_contract_specs(parsed['root'])
    if specs:
        instrument.contract_size = specs['contract_size']
        instrument.tick_size = specs['tick_size']
        instrument.tick_value = specs['tick_value']

# Extract futures-specific fields
contracts = safe_int(row_dict.get(mapping.get("Contracts")))
ticks = safe_float(row_dict.get(mapping.get("Ticks")))

# Calculate ticks if not provided
if ticks is None and instrument.asset_class == 'futures' and entry_price and exit_price:
    ticks = calculate_ticks(entry_price, exit_price, side, instrument.tick_size)

trade.contracts = contracts
trade.ticks = ticks
```

### 3.3 Futures-Specific Metrics

**Add to routes_metrics.py:**
```python
@router.get("/metrics/futures-summary")
def get_futures_summary(...):
    """
    Get futures-specific metrics:
    - Total ticks won/lost
    - Average ticks per trade
    - Win rate by ticks
    - Average contracts traded
    - Performance by contract (ES vs NQ vs CL, etc.)
    - Expiration warnings (contracts expiring soon)
    """
    # Similar structure to forex_summary but for ticks
    pass
```

### 3.4 UI Enhancements for Futures

**Trade detail page:**
```tsx
{trade.asset_class === 'futures' && (
  <div className="futures-details">
    <div className="stat-row">
      <span className="label">Contracts:</span>
      <span className="value">{trade.contracts}</span>
    </div>
    <div className="stat-row">
      <span className="label">Ticks:</span>
      <span className={`value ${trade.ticks >= 0 ? 'text-green-400' : 'text-red-400'}`}>
        {trade.ticks >= 0 ? '+' : ''}{trade.ticks} ticks
      </span>
    </div>
    {instrument.contract_month && (
      <div className="stat-row">
        <span className="label">Contract:</span>
        <span className="value">{instrument.contract_month}</span>
      </div>
    )}
    {instrument.expiration_date && (
      <div className="stat-row">
        <span className="label">Expiration:</span>
        <span className="value">{formatDate(instrument.expiration_date)}</span>
        {isExpiringSoon(instrument.expiration_date) && (
          <span className="badge badge-warning ml-2">Expiring Soon</span>
        )}
      </div>
    )}
  </div>
)}
```

**Dashboard expiration warnings:**
```tsx
// Show banner for expiring contracts
{expiringContracts.length > 0 && (
  <div className="alert alert-warning">
    <strong>Expiring Contracts:</strong> {expiringContracts.length} contracts expire within 7 days.
    <Link href="/instruments">Manage →</Link>
  </div>
)}
```

---

## Testing Strategy

### Unit Tests

**test_forex_utils.py:**
```python
def test_calculate_pips_eurusd():
    pips = calculate_pips("EURUSD", 1.1000, 1.1010, "buy")
    assert pips == 10.0

def test_calculate_pips_usdjpy():
    pips = calculate_pips("USDJPY", 110.00, 110.10, "buy")
    assert pips == 10.0

def test_detect_pip_location():
    assert detect_pip_location("EURUSD") == 10000
    assert detect_pip_location("USDJPY") == 10
    assert detect_pip_location("XAUUSD") == 100

def test_infer_lot_size():
    assert infer_lot_size_from_qty(100000) == 1.0
    assert infer_lot_size_from_qty(10000) == 0.1
```

**test_futures_utils.py:**
```python
def test_parse_futures_symbol():
    result = parse_futures_symbol("ESH25")
    assert result['root'] == 'ES'
    assert result['month'] == 'MAR'
    assert result['full_year'] == 2025

def test_calculate_ticks():
    ticks = calculate_ticks(4500.00, 4502.00, "buy", 0.25)
    assert ticks == 8.0  # 2 points / 0.25 tick size
```

### Integration Tests

**test_forex_import.py:**
```python
def test_import_ftmo_csv_with_pips(client, auth_headers):
    """Test importing FTMO CSV with forex-specific fields"""
    # Upload FTMO example CSV
    # Verify lot_size, pips, swap are correctly imported
    # Verify instrument.asset_class is set to 'forex'
```

**test_futures_import.py:**
```python
def test_import_tradovate_csv(client, auth_headers):
    """Test importing Tradovate CSV with futures contracts"""
    # Upload futures trade CSV
    # Verify contracts, ticks are correctly imported
    # Verify instrument.asset_class is set to 'futures'
    # Verify contract month parsing
```

---

## Migration Plan

### Step 1: Database Migration
Run Alembic migration 0018 to add new columns.

### Step 2: Migrate Existing Data
```sql
-- Set all existing instruments to forex (per user requirement)
UPDATE instruments SET asset_class = 'forex' WHERE asset_class IS NULL OR asset_class = '';

-- Set pip_location based on symbol
UPDATE instruments SET pip_location = 10 WHERE symbol LIKE '%JPY%';
UPDATE instruments SET pip_location = 100 WHERE symbol LIKE '%XAU%' OR symbol LIKE '%XAG%';
UPDATE instruments SET pip_location = 10000 WHERE pip_location IS NULL;
```

### Step 3: Backfill Pips for Existing Trades
Create a one-time script to calculate pips for existing trades:
```python
# api/scripts/backfill_pips.py
from app.db import SessionLocal
from app.models import Trade, Instrument
from app.forex_utils import calculate_pips

db = SessionLocal()
trades = db.query(Trade).join(Instrument).filter(Instrument.asset_class == 'forex').all()

for trade in trades:
    if trade.pips is None and trade.entry_price and trade.exit_price:
        instrument = db.query(Instrument).get(trade.instrument_id)
        trade.pips = calculate_pips(
            instrument.symbol,
            trade.entry_price,
            trade.exit_price,
            trade.side,
            instrument.pip_location
        )

db.commit()
print(f"Backfilled pips for {len(trades)} trades")
```

---

## Rollout Plan

### v0.8.0-alpha (Phase 1)
- Database schema updates
- Basic asset class differentiation
- Migration of existing data to forex
- Asset class badges in UI

### v0.8.0-beta (Phase 2)
- Full forex support (pips, lot sizes, swaps)
- FTMO CSV import support
- Forex-specific metrics and dashboard tiles
- Backfill script for existing trades

### v0.8.0 (Phase 3)
- Futures support (ticks, contracts, expiration)
- Tradovate CSV import support (when user sets up account)
- Futures-specific metrics
- Complete documentation and testing

---

## Design Decisions

1. **Equity support:** ✅ Adding equity as third asset class (forex/futures/equity)
2. **Lot size source:** ✅ Smart fallback - use "Volume" if available, else calculate from "Quantity" (qty_units / 100000)
3. **Swap vs Fees:** ✅ Keep swap separate from fees. net_pnl = gross_pnl - fees - swap. Swap only displayed when non-zero (swing traders). Day traders won't see swap clutter.
4. **Instrument metadata management:** API-only sufficient for now, UI management can be added later if needed
5. **Backfill strategy:** ✅ One-time backfill script for existing trades + calculate-on-import for new trades
6. **Futures CSV format:** Implement Phase 3 with standard futures CSV format, test with Tradovate once account is set up

---

## References

- FTMO CSV example: `/docs/examples/ftmo-example-trades.csv`
- Current import logic: `api/app/routes_uploads.py`
- Current trade model: `api/app/models.py`
- Pip calculation standard: https://www.babypips.com/learn/forex/pips-and-pipettes
