const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatUsdAmount(value: string | number): string {
  const numericValue = typeof value === 'string' ? parseFloat(value) : value;
  return usdFormatter.format(numericValue);
}
