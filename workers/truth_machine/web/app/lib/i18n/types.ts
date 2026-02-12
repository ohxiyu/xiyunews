/**
 * i18n Type Definitions
 *
 * Only includes keys for REAL, implemented features.
 * No fake pump.fun remnants.
 */

export type Lang = 'en' | 'zh';

export const SUPPORTED_LANGS: Lang[] = ['en', 'zh'];
export const DEFAULT_LANG: Lang = 'en';
export const STORAGE_KEY = 'qwe_lang';
export const QUERY_KEY = 'lang';

// Translation keys - only real UI text
export interface TranslationDict {
  // Sidebar (minimal - only trending)
  'sidebar.trending': string;

  // Header (no search, no login)
  'header.langEn': string;
  'header.langZh': string;
  'header.followTwitter': string;

  // Page titles
  'page.trending': string;

  // View modes
  'view.grid': string;
  'view.list': string;
  'view.compact': string;
  'view.full': string;

  // Market card
  'card.yes': string;
  'card.no': string;
  'card.volume': string;
  'card.liquidity': string;
  'card.open': string;

  // States
  'state.loading': string;
  'state.error': string;
  'state.retry': string;
  'state.noData': string;
  'state.empty': string;
  'state.emptyDesc': string;

  // Time
  'time.secondsAgo': string;
  'time.minutesAgo': string;
  'time.hoursAgo': string;
  'time.justNow': string;

  // Controls
  'controls.autoRefresh': string;

  // Footer
  'footer.text': string;

  // Errors
  'error.fetchFailed': string;
  'error.networkError': string;
}

export type TranslationKey = keyof TranslationDict;

// For interpolation: t("key", { name: "value" })
export type TranslationParams = Record<string, string | number>;
