#!/usr/bin/env python3
"""
Backfill script to calculate pips for existing forex trades.

This script:
1. Finds all trades for forex instruments that don't have pips calculated
2. Calculates pips based on entry/exit prices and instrument pip_location
3. Updates the trades with calculated pips

Usage:
    python scripts/backfill_pips.py
    # or via docker:
    docker compose run --rm api python scripts/backfill_pips.py
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models import Trade, Instrument
from app.forex_utils import calculate_pips, infer_lot_size_from_qty


def backfill_pips():
    """Calculate and backfill pips for existing forex trades."""
    db = SessionLocal()
    try:
        # Find all forex trades
        trades = (
            db.query(Trade, Instrument)
            .join(Instrument, Trade.instrument_id == Instrument.id)
            .filter(Instrument.asset_class == 'forex')
            .all()
        )

        print(f"Found {len(trades)} forex trades")

        updated_pips = 0
        updated_lots = 0
        skipped = 0

        for trade, instrument in trades:
            needs_update = False

            # Calculate pips if not set and we have prices
            if (
                trade.pips is None
                and trade.entry_price is not None
                and trade.exit_price is not None
            ):
                pips = calculate_pips(
                    instrument.symbol,
                    trade.entry_price,
                    trade.exit_price,
                    trade.side,
                    instrument.pip_location,
                )
                if pips is not None:
                    trade.pips = pips
                    needs_update = True
                    updated_pips += 1

            # Infer lot_size if not set and we have qty_units
            if trade.lot_size is None and trade.qty_units is not None:
                lot_size = infer_lot_size_from_qty(trade.qty_units, instrument.symbol)
                if lot_size is not None:
                    trade.lot_size = lot_size
                    needs_update = True
                    updated_lots += 1

            if not needs_update:
                skipped += 1

        # Commit all changes
        db.commit()

        print(f"\n✅ Backfill complete!")
        print(f"  - {updated_pips} trades updated with calculated pips")
        print(f"  - {updated_lots} trades updated with inferred lot size")
        print(f"  - {skipped} trades skipped (already had pip/lot data or missing prices)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during backfill: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🔄 Starting pip backfill for forex trades...")
    backfill_pips()
