export const formatUsd = (value: number, opts: { decimals?: number } = {}): string => {
  const decimals = opts.decimals ?? 0;
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

export const formatPct = (value: number, decimals = 1): string => {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
};

export const formatProb = (value: number, decimals = 0): string =>
  `${(value * 100).toFixed(decimals)}%`;

export const formatNumber = (value: number, decimals = 0): string =>
  value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

export const formatDateEs = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString('es-AR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
};
