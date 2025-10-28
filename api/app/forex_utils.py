"""
Forex trading utilities for pip calculations and lot size conversions.
"""


def detect_pip_location(symbol: str) -> int:
    """
    Detect pip location based on currency pair.

    Args:
        symbol: Currency pair (e.g., EURUSD, GBPJPY, XAUUSD)

    Returns:
        10 for JPY pairs (0.01 = 1 pip)
        100 for exotic pairs and metals (0.01 = 1 pip)
        10000 for most pairs (0.0001 = 1 pip)

    Examples:
        >>> detect_pip_location("EURUSD")
        10000
        >>> detect_pip_location("USDJPY")
        10
        >>> detect_pip_location("XAUUSD")
        100
    """
    symbol_upper = symbol.upper().replace('/', '')

    # JPY pairs use 2 decimal places (0.01 = 1 pip)
    if 'JPY' in symbol_upper:
        return 10

    # Metals and some exotics use 2 decimal places
    if any(x in symbol_upper for x in ['XAU', 'XAG', 'GOLD', 'SILVER']):
        return 100

    # Most major pairs use 4 decimal places (0.0001 = 1 pip)
    return 10000


def calculate_pips(
    symbol: str,
    entry_price: float,
    exit_price: float,
    side: str,
    pip_location: int = None
) -> float:
    """
    Calculate pip difference for a forex trade.

    Args:
        symbol: Currency pair (e.g., EURUSD, GBPJPY)
        entry_price: Entry price
        exit_price: Exit price
        side: 'buy' or 'sell' (case insensitive)
        pip_location: Override pip location (optional)

    Returns:
        Pip value (positive for profit, negative for loss)

    Examples:
        >>> calculate_pips("EURUSD", 1.1000, 1.1010, "buy")
        10.0
        >>> calculate_pips("EURUSD", 1.1000, 1.0990, "buy")
        -10.0
        >>> calculate_pips("USDJPY", 110.00, 110.10, "buy")
        10.0
        >>> calculate_pips("EURUSD", 1.1000, 1.0990, "sell")
        10.0
    """
    if entry_price is None or exit_price is None:
        return None

    if pip_location is None:
        pip_location = detect_pip_location(symbol)

    # Calculate price difference
    price_diff = exit_price - entry_price

    # For sell trades, profit is when price goes down
    if side.lower() == 'sell':
        price_diff = -price_diff

    # Convert to pips
    pips = price_diff * pip_location
    return round(pips, 2)


def infer_lot_size_from_qty(qty_units: float, symbol: str = None) -> float:
    """
    Infer lot size from quantity units.

    Standard forex lot sizes:
    - 1.0 lot = 100,000 units (standard lot)
    - 0.1 lot = 10,000 units (mini lot)
    - 0.01 lot = 1,000 units (micro lot)

    Args:
        qty_units: Number of currency units
        symbol: Currency pair (optional, for future enhancements)

    Returns:
        Lot size (1.0, 0.1, 0.01, etc.)

    Examples:
        >>> infer_lot_size_from_qty(100000)
        1.0
        >>> infer_lot_size_from_qty(10000)
        0.1
        >>> infer_lot_size_from_qty(1000)
        0.01
        >>> infer_lot_size_from_qty(182000)
        1.82
    """
    if qty_units is None:
        return None

    # Standard lot = 100,000 units of base currency
    standard_lot_units = 100000
    lot_size = qty_units / standard_lot_units
    return round(lot_size, 2)


def calculate_lot_value(symbol: str, lot_size: float, price: float) -> float:
    """
    Calculate notional value of a forex position.

    Args:
        symbol: Currency pair
        lot_size: Lot size (1.0, 0.1, etc.)
        price: Current price

    Returns:
        Notional value in base currency

    Examples:
        >>> calculate_lot_value("EURUSD", 1.0, 1.1000)
        110000.0
        >>> calculate_lot_value("EURUSD", 0.1, 1.1000)
        11000.0
    """
    if lot_size is None or price is None:
        return None

    # 1 standard lot = 100,000 units of base currency
    standard_lot_units = 100000
    units = lot_size * standard_lot_units
    return units * price


def is_forex_pair(symbol: str) -> bool:
    """
    Detect if symbol is likely a forex pair.

    Args:
        symbol: Symbol to check (e.g., EURUSD, EUR/USD, AAPL)

    Returns:
        True if symbol appears to be a forex pair

    Examples:
        >>> is_forex_pair("EURUSD")
        True
        >>> is_forex_pair("EUR/USD")
        True
        >>> is_forex_pair("GBPJPY")
        True
        >>> is_forex_pair("AAPL")
        False
        >>> is_forex_pair("XAUUSD")
        True
    """
    symbol_upper = symbol.upper().replace('/', '')

    # Known forex currencies
    forex_currencies = {
        'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD',
        'SEK', 'NOK', 'DKK', 'PLN', 'HUF', 'CZK', 'SGD', 'HKD',
        'ZAR', 'MXN', 'TRY', 'CNH', 'RUB'
    }

    # Metals that trade like forex
    metals = {'XAU', 'XAG', 'GOLD', 'SILVER'}

    # Check if it's a metal
    for metal in metals:
        if metal in symbol_upper:
            return True

    # Check if it's exactly 6 chars and both halves are known currencies
    if len(symbol_upper) == 6:
        base = symbol_upper[:3]
        quote = symbol_upper[3:]
        return base in forex_currencies and quote in forex_currencies

    return False


def format_pips(pips: float) -> str:
    """
    Format pips for display.

    Args:
        pips: Pip value

    Returns:
        Formatted string with sign

    Examples:
        >>> format_pips(10.5)
        '+10.5 pips'
        >>> format_pips(-5.2)
        '-5.2 pips'
    """
    if pips is None:
        return '-'

    sign = '+' if pips >= 0 else ''
    return f"{sign}{pips:.1f} pips"
