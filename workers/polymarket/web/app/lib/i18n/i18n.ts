/**
 * i18n utility functions
 */

import {
  Lang,
  SUPPORTED_LANGS,
  DEFAULT_LANG,
  STORAGE_KEY,
  QUERY_KEY,
  TranslationKey,
  TranslationParams,
} from './types';
import { translations } from './translations';

/**
 * Check if a string is a valid Lang
 */
export function isValidLang(lang: string | null | undefined): lang is Lang {
  return !!lang && SUPPORTED_LANGS.includes(lang as Lang);
}

/**
 * Get language from URL query parameter
 */
export function getLangFromUrl(): Lang | null {
  if (typeof window === 'undefined') return null;

  const params = new URLSearchParams(window.location.search);
  const lang = params.get(QUERY_KEY);

  return isValidLang(lang) ? lang : null;
}

/**
 * Get language from localStorage
 */
export function getLangFromStorage(): Lang | null {
  if (typeof window === 'undefined') return null;

  try {
    const lang = localStorage.getItem(STORAGE_KEY);
    return isValidLang(lang) ? lang : null;
  } catch {
    return null;
  }
}

/**
 * Set language to localStorage
 */
export function setLangToStorage(lang: Lang): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // localStorage not available
  }
}

/**
 * Get the resolved language with priority:
 * 1. URL query parameter
 * 2. localStorage
 * 3. Default (en)
 */
export function getResolvedLang(): Lang {
  return getLangFromUrl() ?? getLangFromStorage() ?? DEFAULT_LANG;
}

/**
 * Update URL query parameter without page reload
 */
export function updateUrlLang(lang: Lang, router: { replace: (url: string) => void }): void {
  if (typeof window === 'undefined') return;

  const url = new URL(window.location.href);
  url.searchParams.set(QUERY_KEY, lang);
  router.replace(url.pathname + url.search);
}

/**
 * Translation function with interpolation support
 * Usage: t('card.updatedAt', { time: '5m ago' })
 */
export function translate(
  lang: Lang,
  key: TranslationKey,
  params?: TranslationParams
): string {
  const dict = translations[lang];
  let text = dict[key];

  if (!text) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[i18n] Missing translation for key: "${key}" in lang: "${lang}"`);
    }
    return key;
  }

  // Interpolate parameters: {name} -> value
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    });
  }

  return text;
}

/**
 * Format money value
 * Both locales use same format: $1.2M, $500K, $123
 */
export function formatMoney(value: number | null, _lang: Lang): string | null {
  if (value === null || value === undefined) return null;

  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

/**
 * Format percentage value
 */
export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Format date/time based on locale
 * en: Jan 28, 2026 12:00 UTC
 * zh: 2026/01/28 12:00 UTC
 */
export function formatDateTime(isoDate: string, lang: Lang): string {
  const date = new Date(isoDate);

  if (lang === 'zh') {
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    return `${year}/${month}/${day} ${hours}:${minutes} UTC`;
  }

  // English format
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  }).format(date);
}

/**
 * Get relative time string (e.g., "5m ago" / "5分钟前")
 */
export function getRelativeTime(isoDate: string, lang: Lang): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const seconds = Math.floor((now - then) / 1000);

  if (seconds < 5) {
    return translate(lang, 'time.justNow');
  }
  if (seconds < 60) {
    return translate(lang, 'time.secondsAgo', { n: seconds });
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return translate(lang, 'time.minutesAgo', { n: minutes });
  }
  const hours = Math.floor(minutes / 60);
  return translate(lang, 'time.hoursAgo', { n: hours });
}
