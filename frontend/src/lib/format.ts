export const NONE = '—';

export function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${JSON.stringify(x)}`);
}

export function humanise(str?: string | null): string {
  if (!str) return '';
  return str
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatClock(timestamp?: string | number | Date | null): string {
  if (!timestamp) return NONE;
  const date = new Date(timestamp);
  if (isNaN(date.getTime())) return String(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null || isNaN(seconds)) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function formatAmount(amount?: number | string | null, currency = 'USD'): string {
  if (amount == null) return NONE;
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return NONE;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(num);
}

export function elapsedSeconds(
  start?: string | number | Date | null,
  end?: string | number | Date | null
): number {
  if (!start) return 0;
  const startTime = new Date(start).getTime();
  const endTime = end ? new Date(end).getTime() : Date.now();
  if (isNaN(startTime) || isNaN(endTime)) return 0;
  return Math.max(0, Math.floor((endTime - startTime) / 1000));
}
