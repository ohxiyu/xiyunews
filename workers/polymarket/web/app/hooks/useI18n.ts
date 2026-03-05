"use client";

import { useI18nContext } from "../components/I18nProvider";

/**
 * Hook to access i18n functionality
 *
 * Usage:
 * const { lang, setLang, t, formatMoney, formatPercent, formatDateTime, getRelativeTime } = useI18n();
 *
 * // Translation
 * t('sidebar.home') // "Home" or "首页"
 * t('card.updatedAt', { time: '5m ago' }) // "Updated 5m ago"
 *
 * // Set language
 * setLang('zh') // switches to Chinese, updates URL and localStorage
 *
 * // Formatting
 * formatMoney(1234567) // "$1.2M"
 * formatPercent(0.65) // "65.0%"
 * formatDateTime('2026-01-28T12:00:00Z') // "Jan 28, 2026 12:00 UTC" or "2026/01/28 12:00 UTC"
 * getRelativeTime('2026-01-28T12:00:00Z') // "5m ago" or "5分钟前"
 */
export function useI18n() {
  return useI18nContext();
}
