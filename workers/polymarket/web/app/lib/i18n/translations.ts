/**
 * Translation dictionaries for all supported languages
 *
 * Only contains keys for REAL, implemented features:
 * - Sidebar: Logo + Trending nav
 * - Header: Time + Language toggle
 * - TabsBar: Platform tabs + View controls
 * - MarketCard: Rank, Title, Odds, Volume, Liquidity
 * - States: Loading, Error, Empty
 */

import { Lang, TranslationDict } from './types';

const en: TranslationDict = {
  // Sidebar (minimal)
  'sidebar.trending': 'Trending',

  // Header
  'header.langEn': 'EN',
  'header.langZh': '中文',
  'header.followTwitter': 'Follow on X',

  // Page titles
  'page.trending': 'Trending Markets',

  // View modes
  'view.grid': 'Grid',
  'view.list': 'List',
  'view.compact': 'Compact',
  'view.full': 'Full',

  // Market card
  'card.yes': 'Yes',
  'card.no': 'No',
  'card.volume': '24h Volume',
  'card.liquidity': 'Liquidity',
  'card.open': 'Open',

  // States
  'state.loading': 'Loading...',
  'state.error': 'Failed to load',
  'state.retry': 'Retry',
  'state.noData': 'No markets available',
  'state.empty': 'No Data Available',
  'state.emptyDesc': 'No markets available for this platform yet. Try selecting a different platform.',

  // Time
  'time.secondsAgo': '{n}s ago',
  'time.minutesAgo': '{n}m ago',
  'time.hoursAgo': '{n}h ago',
  'time.justNow': 'Just now',

  // Controls
  'controls.autoRefresh': 'Auto-refresh',

  // Footer
  'footer.text': 'Qwe Truth Machine · Multi-platform Prediction Market Tracker',

  // Errors
  'error.fetchFailed': 'Failed to fetch data',
  'error.networkError': 'Network error',
};

const zh: TranslationDict = {
  // Sidebar (minimal)
  'sidebar.trending': '热榜',

  // Header
  'header.langEn': 'EN',
  'header.langZh': '中文',
  'header.followTwitter': '关注开发者',

  // Page titles
  'page.trending': '热门市场',

  // View modes
  'view.grid': '网格',
  'view.list': '列表',
  'view.compact': '紧凑',
  'view.full': '完整',

  // Market card
  'card.yes': '是',
  'card.no': '否',
  'card.volume': '24h交易量',
  'card.liquidity': '流动性',
  'card.open': '打开',

  // States
  'state.loading': '加载中...',
  'state.error': '加载失败',
  'state.retry': '重试',
  'state.noData': '暂无市场数据',
  'state.empty': '暂无数据',
  'state.emptyDesc': '该平台暂无市场数据，请尝试切换其他平台。',

  // Time
  'time.secondsAgo': '{n}秒前',
  'time.minutesAgo': '{n}分钟前',
  'time.hoursAgo': '{n}小时前',
  'time.justNow': '刚刚',

  // Controls
  'controls.autoRefresh': '自动刷新',

  // Footer
  'footer.text': 'Qwe Truth Machine · 多平台预测市场追踪',

  // Errors
  'error.fetchFailed': '获取数据失败',
  'error.networkError': '网络错误',
};

export const translations: Record<Lang, TranslationDict> = {
  en,
  zh,
};
