/**
 * Utility functions for QweTruthMachine
 */

/**
 * Format volume/liquidity values to human readable format
 * @param val - The numeric value to format
 * @returns Formatted string like "$1.2M" or "$500K"
 */
export function formatVolume(val: number | null): string | null {
  if (val === null || val === undefined) return null;
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

/**
 * Format percentage value
 * @param val - Value between 0 and 1
 * @returns Formatted string like "65.0%"
 */
export function formatPercent(val: number): string {
  return `${(val * 100).toFixed(1)}%`;
}

/**
 * Get relative time since a date
 * @param isoDate - ISO date string
 * @param lang - Language code ('zh' or 'en')
 * @returns Formatted relative time string
 */
export function getTimeSince(isoDate: string, lang: 'zh' | 'en' = 'zh'): string {
  const suffixes = {
    zh: { seconds: '秒前', minutes: '分钟前', hours: '小时前' },
    en: { seconds: 's ago', minutes: 'm ago', hours: 'h ago' },
  };

  const s = suffixes[lang];
  const now = new Date().getTime();
  const then = new Date(isoDate).getTime();
  const seconds = Math.floor((now - then) / 1000);

  if (seconds < 60) return `${seconds}${s.seconds}`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}${s.minutes}`;
  const hours = Math.floor(minutes / 60);
  return `${hours}${s.hours}`;
}

/**
 * Format UTC time string
 * @returns Current UTC time in ISO format without milliseconds
 */
export function formatUTCTime(): string {
  return new Date().toISOString().slice(0, 19) + 'Z';
}

/**
 * Classname helper - joins class names with space
 * @param classes - Array of class names (can include falsy values)
 * @returns Joined class string
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
