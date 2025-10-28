interface AssetClassBadgeProps {
  assetClass: string | null | undefined;
}

export function AssetClassBadge({ assetClass }: AssetClassBadgeProps) {
  if (!assetClass) return null;

  const colors: Record<string, string> = {
    forex: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    futures: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    equity: 'bg-green-500/20 text-green-300 border-green-500/30',
  };

  const colorClass = colors[assetClass.toLowerCase()] || 'bg-gray-500/20 text-gray-300 border-gray-500/30';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}>
      {assetClass.toUpperCase()}
    </span>
  );
}
