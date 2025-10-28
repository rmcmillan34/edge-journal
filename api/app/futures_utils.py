"""
Futures trading utilities for contract parsing and tick calculations.
"""
import re
from datetime import date, datetime
from typing import Optional, Dict


# Futures month codes (standard CME convention)
MONTH_CODES = {
    'F': ('JAN', 1),  'G': ('FEB', 2),  'H': ('MAR', 3),
    'J': ('APR', 4),  'K': ('MAY', 5),  'M': ('JUN', 6),
    'N': ('JUL', 7),  'Q': ('AUG', 8),  'U': ('SEP', 9),
    'V': ('OCT', 10), 'X': ('NOV', 11), 'Z': ('DEC', 12)
}

# Reverse lookup
MONTH_TO_CODE = {month: code for code, (month, _) in MONTH_CODES.items()}


# Contract specifications for common futures
CONTRACT_SPECS = {
    # E-mini Index Futures
    'ES': {
        'name': 'E-mini S&P 500',
        'exchange': 'CME',
        'contract_size': 50,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'currency': 'USD',
    },
    'NQ': {
        'name': 'E-mini Nasdaq-100',
        'exchange': 'CME',
        'contract_size': 20,
        'tick_size': 0.25,
        'tick_value': 5.00,
        'currency': 'USD',
    },
    'YM': {
        'name': 'E-mini Dow',
        'exchange': 'CBOT',
        'contract_size': 5,
        'tick_size': 1.0,
        'tick_value': 5.00,
        'currency': 'USD',
    },
    'RTY': {
        'name': 'E-mini Russell 2000',
        'exchange': 'CME',
        'contract_size': 50,
        'tick_size': 0.10,
        'tick_value': 5.00,
        'currency': 'USD',
    },
    # Micro E-mini Futures
    'MES': {
        'name': 'Micro E-mini S&P 500',
        'exchange': 'CME',
        'contract_size': 5,
        'tick_size': 0.25,
        'tick_value': 1.25,
        'currency': 'USD',
    },
    'MNQ': {
        'name': 'Micro E-mini Nasdaq-100',
        'exchange': 'CME',
        'contract_size': 2,
        'tick_size': 0.25,
        'tick_value': 0.50,
        'currency': 'USD',
    },
    'MYM': {
        'name': 'Micro E-mini Dow',
        'exchange': 'CBOT',
        'contract_size': 0.5,
        'tick_size': 1.0,
        'tick_value': 0.50,
        'currency': 'USD',
    },
    'M2K': {
        'name': 'Micro E-mini Russell 2000',
        'exchange': 'CME',
        'contract_size': 5,
        'tick_size': 0.10,
        'tick_value': 0.50,
        'currency': 'USD',
    },
    # Energy Futures
    'CL': {
        'name': 'Crude Oil',
        'exchange': 'NYMEX',
        'contract_size': 1000,
        'tick_size': 0.01,
        'tick_value': 10.00,
        'currency': 'USD',
    },
    'NG': {
        'name': 'Natural Gas',
        'exchange': 'NYMEX',
        'contract_size': 10000,
        'tick_size': 0.001,
        'tick_value': 10.00,
        'currency': 'USD',
    },
    'RB': {
        'name': 'RBOB Gasoline',
        'exchange': 'NYMEX',
        'contract_size': 42000,
        'tick_size': 0.0001,
        'tick_value': 4.20,
        'currency': 'USD',
    },
    # Metals Futures
    'GC': {
        'name': 'Gold',
        'exchange': 'COMEX',
        'contract_size': 100,
        'tick_size': 0.10,
        'tick_value': 10.00,
        'currency': 'USD',
    },
    'SI': {
        'name': 'Silver',
        'exchange': 'COMEX',
        'contract_size': 5000,
        'tick_size': 0.005,
        'tick_value': 25.00,
        'currency': 'USD',
    },
    'HG': {
        'name': 'Copper',
        'exchange': 'COMEX',
        'contract_size': 25000,
        'tick_size': 0.0005,
        'tick_value': 12.50,
        'currency': 'USD',
    },
    # Agricultural Futures
    'ZC': {
        'name': 'Corn',
        'exchange': 'CBOT',
        'contract_size': 5000,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'currency': 'USD',
    },
    'ZS': {
        'name': 'Soybeans',
        'exchange': 'CBOT',
        'contract_size': 5000,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'currency': 'USD',
    },
    'ZW': {
        'name': 'Wheat',
        'exchange': 'CBOT',
        'contract_size': 5000,
        'tick_size': 0.25,
        'tick_value': 12.50,
        'currency': 'USD',
    },
}


def parse_futures_symbol(symbol: str) -> Optional[Dict]:
    """
    Parse futures symbol to extract root, month, year.

    Args:
        symbol: Futures contract symbol (e.g., ESH25, NQM2024, CLZ4)

    Returns:
        Dict with root, month_code, month_name, year, full_year, or None if not a futures symbol

    Examples:
        >>> parse_futures_symbol("ESH25")
        {'root': 'ES', 'month_code': 'H', 'month': 'MAR', 'year': '25', 'full_year': 2025}
        >>> parse_futures_symbol("NQM2024")
        {'root': 'NQ', 'month_code': 'M', 'month': 'JUN', 'year': '2024', 'full_year': 2024}
        >>> parse_futures_symbol("AAPL")
        None
    """
    # Match patterns like ESH25, NQM2024, CLZ4
    # Root can be 1-4 letters, followed by month code, followed by 2 or 4 digit year
    match = re.match(r'^([A-Z]{1,4})([FGHJKMNQUVXZ])(\d{2,4})$', symbol.upper())
    if not match:
        return None

    root, month_code, year_str = match.groups()

    if month_code not in MONTH_CODES:
        return None

    month_name, month_num = MONTH_CODES[month_code]

    # Handle 2-digit or 4-digit year
    if len(year_str) == 2:
        year_int = int(year_str)
        # Assume 20xx for years 00-50, 19xx for 51-99
        if year_int <= 50:
            full_year = 2000 + year_int
        else:
            full_year = 1900 + year_int
    else:
        full_year = int(year_str)

    return {
        'root': root,
        'month_code': month_code,
        'month': month_name,
        'month_num': month_num,
        'year': year_str,
        'full_year': full_year,
    }


def get_contract_specs(root: str) -> Optional[Dict]:
    """
    Return contract specifications for a futures root symbol.

    Args:
        root: Futures root symbol (e.g., ES, NQ, CL)

    Returns:
        Dict with contract specs (name, exchange, contract_size, tick_size, tick_value, currency)

    Examples:
        >>> get_contract_specs("ES")
        {'name': 'E-mini S&P 500', 'exchange': 'CME', 'contract_size': 50, ...}
        >>> get_contract_specs("UNKNOWN")
        None
    """
    return CONTRACT_SPECS.get(root.upper())


def calculate_ticks(
    entry_price: float,
    exit_price: float,
    side: str,
    tick_size: float
) -> Optional[float]:
    """
    Calculate tick-based P&L for futures.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        side: 'buy' or 'sell' (case insensitive)
        tick_size: Tick size for the contract

    Returns:
        Tick value (positive for profit, negative for loss)

    Examples:
        >>> calculate_ticks(4500.00, 4502.00, "buy", 0.25)
        8.0
        >>> calculate_ticks(4500.00, 4498.00, "buy", 0.25)
        -8.0
        >>> calculate_ticks(4500.00, 4498.00, "sell", 0.25)
        8.0
    """
    if entry_price is None or exit_price is None or tick_size is None:
        return None

    # Calculate price difference
    price_diff = exit_price - entry_price

    # For sell trades, profit is when price goes down
    if side.lower() == 'sell':
        price_diff = -price_diff

    # Convert to ticks
    ticks = price_diff / tick_size
    return round(ticks, 2)


def is_futures_symbol(symbol: str) -> bool:
    """
    Detect if symbol is likely a futures contract.

    Args:
        symbol: Symbol to check (e.g., ESH25, AAPL)

    Returns:
        True if symbol appears to be a futures contract

    Examples:
        >>> is_futures_symbol("ESH25")
        True
        >>> is_futures_symbol("NQM2024")
        True
        >>> is_futures_symbol("AAPL")
        False
        >>> is_futures_symbol("EURUSD")
        False
    """
    return parse_futures_symbol(symbol) is not None


def format_contract_month(symbol: str) -> Optional[str]:
    """
    Format contract month for display.

    Args:
        symbol: Futures symbol (e.g., ESH25)

    Returns:
        Formatted month string (e.g., "MAR 2025") or None

    Examples:
        >>> format_contract_month("ESH25")
        'MAR 2025'
        >>> format_contract_month("NQM2024")
        'JUN 2024'
        >>> format_contract_month("AAPL")
        None
    """
    parsed = parse_futures_symbol(symbol)
    if not parsed:
        return None

    return f"{parsed['month']} {parsed['full_year']}"


def format_ticks(ticks: float) -> str:
    """
    Format ticks for display.

    Args:
        ticks: Tick value

    Returns:
        Formatted string with sign

    Examples:
        >>> format_ticks(10.5)
        '+10.5 ticks'
        >>> format_ticks(-5.0)
        '-5.0 ticks'
    """
    if ticks is None:
        return '-'

    sign = '+' if ticks >= 0 else ''
    return f"{sign}{ticks:.1f} ticks"


def get_expiration_estimate(symbol: str) -> Optional[date]:
    """
    Estimate expiration date for a futures contract.

    Note: This is an approximation. Actual expiration dates vary by contract
    and should ideally be looked up from exchange data.

    Args:
        symbol: Futures symbol (e.g., ESH25)

    Returns:
        Estimated expiration date or None

    Examples:
        >>> get_expiration_estimate("ESH25")
        datetime.date(2025, 3, 15)  # Approximate
    """
    parsed = parse_futures_symbol(symbol)
    if not parsed:
        return None

    # Most index futures expire on the 3rd Friday of the contract month
    # This is a rough estimate - real expiration dates should come from exchange data
    year = parsed['full_year']
    month = parsed['month_num']

    # Find 3rd Friday
    from calendar import monthcalendar, FRIDAY
    cal = monthcalendar(year, month)
    fridays = [week[FRIDAY] for week in cal if week[FRIDAY] != 0]

    if len(fridays) >= 3:
        expiration_day = fridays[2]  # 3rd Friday
        return date(year, month, expiration_day)

    return None
