/**
 * Get the quantity label based on asset class
 */
export function getQuantityLabel(assetClass: string | null | undefined): string {
  if (!assetClass) return 'Quantity';

  switch (assetClass.toLowerCase()) {
    case 'forex':
      return 'Lots';
    case 'futures':
      return 'Contracts';
    case 'equity':
      return 'Shares';
    default:
      return 'Quantity';
  }
}

/**
 * Format quantity based on asset class
 */
export function formatQuantity(
  assetClass: string | null | undefined,
  value: number | null | undefined
): string {
  if (value === null || value === undefined) return '—';

  const label = getQuantityLabel(assetClass);

  switch (assetClass?.toLowerCase()) {
    case 'forex':
      // Forex lots: show 2 decimal places
      return `${value.toFixed(2)} ${label.toLowerCase()}`;
    case 'futures':
      // Futures contracts: show as integer
      return `${Math.round(value)} ${label.toLowerCase()}`;
    case 'equity':
      // Equity shares: show as integer
      return `${Math.round(value)} ${label.toLowerCase()}`;
    default:
      return `${value} ${label.toLowerCase()}`;
  }
}

/**
 * Format pips for forex trades
 */
export function formatPips(pips: number | null | undefined): string {
  if (pips === null || pips === undefined) return '—';

  const sign = pips >= 0 ? '+' : '';
  return `${sign}${pips.toFixed(1)} pips`;
}

/**
 * Format ticks for futures trades
 */
export function formatTicks(ticks: number | null | undefined): string {
  if (ticks === null || ticks === undefined) return '—';

  const sign = ticks >= 0 ? '+' : '';
  return `${sign}${ticks.toFixed(1)} ticks`;
}

/**
 * Check if trade has forex-specific data
 */
export function hasForexData(trade: any): boolean {
  return (
    trade.asset_class === 'forex' &&
    (trade.lot_size !== null ||
      trade.pips !== null ||
      trade.swap !== null ||
      trade.stop_loss !== null ||
      trade.take_profit !== null)
  );
}

/**
 * Check if trade has futures-specific data
 */
export function hasFuturesData(trade: any): boolean {
  return (
    trade.asset_class === 'futures' &&
    (trade.contracts !== null || trade.ticks !== null)
  );
}
