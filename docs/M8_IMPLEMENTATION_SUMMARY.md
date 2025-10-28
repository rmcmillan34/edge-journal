# M8: Forex & Futures - Implementation Summary

**Version:** v0.8.1
**Status:** ✅ Complete
**Date:** October 28, 2025

## Overview

M8 adds comprehensive support for forex and futures trading to Edge-Journal. The system now properly differentiates between forex, futures, and equity asset classes, with specialized features for each.

---

## Phase 1: Foundation - Asset Class Support

### Database Schema (Migration 0019)

**Instruments Table - New Fields:**
- `pip_location` (Integer): For forex - pip decimal location (10/100/10000)
- `contract_size` (Integer): For futures - units per contract
- `tick_size` (Numeric): For futures - minimum price increment
- `tick_value` (Numeric): For futures - dollar value per tick
- `expiration_date` (Date): For futures - contract expiration
- `contract_month` (String): For futures - contract month (e.g., "MAR 2025")
- `asset_class` (String): Now NOT NULL with default 'forex'

**Trades Table - New Fields:**
- `lot_size` (Numeric): Forex lot size (1.0, 0.1, 0.01)
- `pips` (Numeric): Forex pip-based P&L
- `swap` (Numeric): Forex overnight interest
- `stop_loss` (Numeric): Forex stop loss level
- `take_profit` (Numeric): Forex take profit level
- `contracts` (Integer): Futures contract count
- `ticks` (Numeric): Futures tick-based P&L

### Backend Updates

- Updated `Instrument` and `Trade` models with new fields
- Updated Pydantic schemas (`TradeOut`, `TradeCreate`, `TradeUpdate`)
- Updated `routes_trades.py` to include asset_class and forex/futures fields
- Auto-migration of existing data to forex asset class

### Frontend Updates

- **AssetClassBadge Component**: Blue (forex), Purple (futures), Green (equity)
- **Asset Class Utilities** (`web/utils/assetClass.ts`):
  - `getQuantityLabel()` - Returns "Lots", "Contracts", or "Shares"
  - `formatPips()` - Formats pip values with sign
  - `formatTicks()` - Formats tick values with sign
  - `hasForexData()` - Checks for forex-specific data
  - `hasFuturesData()` - Checks for futures-specific data
- Trade list shows asset class badges and pip P&L
- Trade detail page shows forex/futures-specific sections

---

## Phase 2: Forex Support

### Forex Utilities (`api/app/forex_utils.py`)

- **detect_pip_location()**: Auto-detects pip location (10 for JPY, 100 for metals, 10000 for majors)
- **calculate_pips()**: Calculates pip P&L from entry/exit prices and trade side
- **infer_lot_size_from_qty()**: Converts quantity units to lot size (100k units = 1.0 lot)
- **is_forex_pair()**: Detects forex currency pairs
- **calculate_lot_value()**: Calculates notional position value
- **format_pips()**: Formats pips for display

### CSV Import Enhancements

**FTMO Format Support:**
- Auto-detects forex pairs and sets asset_class='forex' + pip_location
- FTMO preset includes forex-specific mappings:
  - `Volume` → `lot_size`
  - `Pips` → `pips`
  - `Swap` → `swap`
  - `SL` → `stop_loss`
  - `TP` → `take_profit`

**Smart Fallbacks:**
- Lot size: Uses "Volume" column if available, calculates from qty_units otherwise
- Pips: Uses "Pips" column if available, calculates from entry/exit prices otherwise
- Instrument auto-updates with forex metadata when detected

### Backfill Script

- Created `/api/scripts/backfill_pips.py`
- Calculates pips for existing trades
- Infers lot sizes from quantity units
- Run with: `docker compose run --rm api python scripts/backfill_pips.py`
- Successfully backfilled 19 existing forex trades

### Forex Metrics Endpoint

**GET /metrics/forex-summary**

Returns:
- `total_pips`: Total pips won/lost
- `avg_pips_per_trade`: Average pips per trade
- `pip_win_rate`: Win rate by pips (%)
- `avg_lot_size`: Average lot size traded
- `best_pip_trade`: Best pip trade
- `worst_pip_trade`: Worst pip trade
- `pip_winners`: Count of winning pip trades
- `pip_losers`: Count of losing pip trades

Supports filters: `account_id`, `start_date`, `end_date`

---

## Phase 3: Futures Support

### Futures Utilities (`api/app/futures_utils.py`)

**Contract Specifications:**
- Built-in specs for 20+ common futures contracts:
  - Index: ES, NQ, YM, RTY, MES, MNQ, MYM, M2K
  - Energy: CL, NG, RB
  - Metals: GC, SI, HG
  - Grains: ZC, ZS, ZW

Each spec includes: name, exchange, contract_size, tick_size, tick_value

**Core Functions:**
- **parse_futures_symbol()**: Parses ESH25 → {root: 'ES', month: 'MAR', full_year: 2025}
- **get_contract_specs()**: Returns contract specifications by root
- **calculate_ticks()**: Calculates tick-based P&L
- **is_futures_symbol()**: Detects futures contract symbols
- **format_contract_month()**: Formats ESH25 → "MAR 2025"
- **get_expiration_estimate()**: Estimates 3rd Friday expiration
- **format_ticks()**: Formats ticks for display

### CSV Import for Futures

**Auto-Detection:**
- Detects futures symbols (ESH25, NQM2024, etc.)
- Sets asset_class='futures' + contract metadata
- Populates contract_month, expiration_date, tick_size, tick_value

**Smart Fallbacks:**
- Contracts: Uses qty_units if "Contracts" column not available
- Ticks: Calculates from entry/exit prices if not provided

**Broker Presets:**
- **Tradovate**: Full support for Tradovate CSV exports
- **NinjaTrader**: Updated with futures-specific field mappings

### Futures Metrics Endpoint

**GET /metrics/futures-summary**

Returns:
- `total_ticks`: Total ticks won/lost
- `avg_ticks_per_trade`: Average ticks per trade
- `tick_win_rate`: Win rate by ticks (%)
- `avg_contracts`: Average contracts traded
- `best_tick_trade`: Best tick trade
- `worst_tick_trade`: Worst tick trade
- `tick_winners`: Count of winning tick trades
- `tick_losers`: Count of losing tick trades
- `by_contract`: Performance breakdown by contract (ES vs NQ vs CL, etc.)

Supports filters: `account_id`, `start_date`, `end_date`

### Example Data

Created `/docs/examples/futures-example-trades.csv` with sample trades:
- E-mini S&P 500 (ES)
- E-mini Nasdaq (NQ)
- Micro E-mini S&P (MES)
- Crude Oil (CL)
- Gold (GC)

---

## How It Works

### Forex Trade Import Flow

1. **CSV Upload**: User uploads FTMO CSV with forex trades
2. **Auto-Detection**: System detects currency pairs (EURUSD, GBPJPY)
3. **Instrument Creation**: Creates/updates instrument with:
   - `asset_class='forex'`
   - `pip_location` (10 for JPY, 10000 for majors)
4. **Field Extraction**:
   - Volume → lot_size
   - Pips → pips (or calculated if missing)
   - Swap → swap
   - SL/TP → stop_loss/take_profit
5. **Trade Storage**: Saves trade with all forex metadata

### Futures Trade Import Flow

1. **CSV Upload**: User uploads Tradovate CSV with futures trades
2. **Auto-Detection**: System parses futures symbols (ESH25)
3. **Contract Lookup**: Looks up contract specs (ES = E-mini S&P 500)
4. **Instrument Creation**: Creates/updates instrument with:
   - `asset_class='futures'`
   - `contract_month='MAR 2025'`
   - `expiration_date='2025-03-15'`
   - `tick_size=0.25`, `tick_value=12.50`
5. **Field Extraction**:
   - Qty → contracts
   - Ticks → ticks (or calculated if missing)
6. **Trade Storage**: Saves trade with all futures metadata

---

## UI Features

### Trade List

- Asset class badges (forex/futures/equity) below symbol
- Pip P&L shown below $ P&L for forex trades
- Tick P&L shown below $ P&L for futures trades

### Trade Detail Page

**Forex Section (when asset_class='forex'):**
- Lot Size: 1.82 lots
- Pips: +5.9 pips (colored green/red)
- Swap: $0.00
- Stop Loss: 1.34666
- Take Profit: 1.34819

**Futures Section (when asset_class='futures'):**
- Contracts: 2
- Ticks: +22.0 ticks (colored green/red)
- Contract: MAR 2025
- Expiration: 2025-03-15 (with warning if expiring soon)

---

## API Endpoints

### Existing Endpoints (Updated)

- `GET /trades` - Now includes `asset_class`, `lot_size`, `pips`, `swap`, `stop_loss`, `take_profit`, `contracts`, `ticks`
- `GET /trades/{id}` - Same fields for trade detail
- `POST /uploads/commit` - Auto-detects asset class and extracts forex/futures fields

### New Endpoints

- `GET /metrics/forex-summary` - Forex-specific metrics (pips, lots, etc.)
- `GET /metrics/futures-summary` - Futures-specific metrics (ticks, contracts, by-contract breakdown)

---

## Testing

### Backfill Results

Successfully backfilled 19 existing forex trades:
- ✅ 19 trades updated with calculated pips
- ✅ 19 trades updated with inferred lot sizes
- ✅ 0 trades skipped

### Test Data Available

- **Forex**: `/docs/examples/ftmo-example-trades.csv` (10 GBPUSD/EURUSD trades)
- **Futures**: `/docs/examples/futures-example-trades.csv` (10 ES/NQ/MES/CL/GC trades)

### Import Testing

To test FTMO CSV import:
1. Navigate to http://localhost:3000/upload
2. Upload `/docs/examples/ftmo-example-trades.csv`
3. System auto-detects FTMO format
4. Maps Volume → lot_size, Pips → pips, Swap → swap
5. Creates forex instruments with correct pip_location
6. Displays trades with pip P&L

To test Tradovate CSV import:
1. Upload `/docs/examples/futures-example-trades.csv`
2. System detects futures symbols (ESH25, NQM25)
3. Looks up contract specs
4. Maps Qty → contracts, Ticks → ticks
5. Creates futures instruments with contract metadata
6. Displays trades with tick P&L and contract month

---

## Migration Path

### Existing Users

1. **Database Migration**: Alembic 0019 runs automatically on startup (dev mode)
2. **Data Migration**: All existing instruments set to asset_class='forex'
3. **Pip Calculation**: Run backfill script: `docker compose run --rm api python scripts/backfill_pips.py`
4. **No Breaking Changes**: All existing functionality preserved

### New Users

Start fresh with full forex/futures support enabled from day one.

---

## Configuration

### Contract Specifications

Contract specs are hardcoded in `/api/app/futures_utils.py` under `CONTRACT_SPECS` dict. To add a new contract:

```python
'NEW': {
    'name': 'Contract Name',
    'exchange': 'CME',
    'contract_size': 50,
    'tick_size': 0.25,
    'tick_value': 12.50,
    'currency': 'USD',
}
```

### CSV Presets

Presets are defined in `/api/app/routes_uploads.py` under `PRESETS` dict. Supported presets:
- `ftmo` - FTMO forex exports
- `ctrader` - cTrader platform
- `mt5` - MetaTrader 5
- `ninjatrader` - NinjaTrader futures
- `tradovate` - Tradovate futures

---

## Stretch Goals (Future Enhancements)

See `docs/ROADMAP.md` under "M8 Stretch Goals":

1. **Configurable Dashboard Widgets**
   - Drag-and-drop widget layout
   - Forex widgets: pip stats, lot size, pip win rate
   - Futures widgets: tick stats, contracts, by-contract performance
   - Asset class filters

2. **Multi-Currency P&L Conversion**
   - Display P&L in user's base currency
   - Historical FX rates

3. **Swap/Rollover Calendar**
   - Visual calendar of swap charges for swing traders

4. **Contract Expiration Alerts**
   - Dashboard warnings for expiring futures
   - Email/push notifications

5. **Symbol-Level Analytics**
   - Deep dive: EURUSD vs GBPJPY
   - Futures: ES vs NQ performance comparison

---

## Technical Debt & Notes

1. **Expiration Dates**: Currently estimated (3rd Friday), should eventually pull from exchange data
2. **Contract Specs**: Hardcoded, could be moved to database for easier updates
3. **Currency Conversion**: Not yet implemented for multi-currency accounts
4. **Equity Support**: Added but not fully featured (no equity-specific metrics yet)

---

## Files Modified/Created

### Backend

**New Files:**
- `/api/app/forex_utils.py` - Forex calculation utilities
- `/api/app/futures_utils.py` - Futures contract parsing and calculations
- `/api/scripts/backfill_pips.py` - Pip backfill script
- `/api/alembic/versions/0019_forex_futures_support.py` - Database migration

**Modified Files:**
- `/api/app/models.py` - Added forex/futures fields to Instrument and Trade
- `/api/app/schemas.py` - Added forex/futures fields to Pydantic schemas
- `/api/app/routes_trades.py` - Return asset_class and forex/futures fields
- `/api/app/routes_uploads.py` - Auto-detect asset class, extract forex/futures fields
- `/api/app/routes_metrics.py` - Added forex-summary and futures-summary endpoints

### Frontend

**New Files:**
- `/web/components/AssetClassBadge.tsx` - Asset class badge component
- `/web/utils/assetClass.ts` - Asset class utility functions

**Modified Files:**
- `/web/app/trades/page.tsx` - Show asset class badges and pip P&L
- `/web/app/trades/[id]/page.tsx` - Show forex/futures detail sections

### Documentation

**New Files:**
- `/docs/M8_FOREX_FUTURES_TECH_DESIGN.md` - Technical design document
- `/docs/M8_IMPLEMENTATION_SUMMARY.md` - This file
- `/docs/examples/futures-example-trades.csv` - Futures test data

**Modified Files:**
- `/docs/ROADMAP.md` - Marked M8 as complete with all 3 phases
- `/VERSION` - Updated to 0.8.1

---

## Summary

M8 successfully adds comprehensive forex and futures support to Edge-Journal:

- ✅ **Asset class differentiation** - Forex, futures, and equity properly separated
- ✅ **Forex support** - Pips, lot sizes, swaps, SL/TP tracking
- ✅ **Futures support** - Ticks, contracts, expiration dates, contract specs
- ✅ **Auto-detection** - Symbols automatically classified (EURUSD→forex, ESH25→futures)
- ✅ **CSV import** - FTMO, Tradovate, NinjaTrader formats supported
- ✅ **Metrics** - Dedicated forex-summary and futures-summary endpoints
- ✅ **UI** - Asset class badges, pip/tick display, futures contract info
- ✅ **Migration** - Existing data safely migrated to forex
- ✅ **Backfill** - 19 existing trades updated with calculated pips and lot sizes

**Next Milestone:** M9 - Insight Coach (Stretch Goal)
