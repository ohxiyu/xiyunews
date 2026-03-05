"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Lang,
  DEFAULT_LANG,
  QUERY_KEY,
  TranslationKey,
  TranslationParams,
  getResolvedLang,
  setLangToStorage,
  translate,
  formatMoney,
  formatPercent,
  formatDateTime,
  getRelativeTime,
} from "../lib/i18n";

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey, params?: TranslationParams) => string;
  formatMoney: (value: number | null) => string | null;
  formatPercent: (value: number) => string;
  formatDateTime: (isoDate: string) => string;
  getRelativeTime: (isoDate: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

interface I18nProviderProps {
  children: ReactNode;
}

export function I18nProvider({ children }: I18nProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize with default, will be updated after hydration
  const [lang, setLangState] = useState<Lang>(DEFAULT_LANG);
  const [isHydrated, setIsHydrated] = useState(false);

  // Resolve language after hydration
  useEffect(() => {
    const resolved = getResolvedLang();
    setLangState(resolved);
    setIsHydrated(true);
  }, []);

  // Listen to URL changes
  useEffect(() => {
    if (!isHydrated) return;

    const urlLang = searchParams.get(QUERY_KEY);
    if (urlLang === "en" || urlLang === "zh") {
      if (urlLang !== lang) {
        setLangState(urlLang);
        setLangToStorage(urlLang);
      }
    }
  }, [searchParams, isHydrated, lang]);

  // Set language handler
  const setLang = useCallback(
    (newLang: Lang) => {
      if (newLang === lang) return;

      // Update state
      setLangState(newLang);

      // Persist to storage
      setLangToStorage(newLang);

      // Update URL (replace, not push)
      const url = new URL(window.location.href);
      url.searchParams.set(QUERY_KEY, newLang);
      router.replace(url.pathname + url.search);
    },
    [lang, router]
  );

  // Memoized translation function
  const t = useCallback(
    (key: TranslationKey, params?: TranslationParams) => {
      return translate(lang, key, params);
    },
    [lang]
  );

  // Memoized formatters
  const contextValue = useMemo<I18nContextValue>(
    () => ({
      lang,
      setLang,
      t,
      formatMoney: (value) => formatMoney(value, lang),
      formatPercent,
      formatDateTime: (isoDate) => formatDateTime(isoDate, lang),
      getRelativeTime: (isoDate) => getRelativeTime(isoDate, lang),
    }),
    [lang, setLang, t]
  );

  // Prevent flash of wrong language during hydration
  // Return children immediately but with default lang until hydration
  return (
    <I18nContext.Provider value={contextValue}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18nContext(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18nContext must be used within an I18nProvider");
  }
  return context;
}
