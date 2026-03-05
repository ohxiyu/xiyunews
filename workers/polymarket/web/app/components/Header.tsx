"use client";

import { useI18n } from "../hooks/useI18n";

interface HeaderProps {
  currentTime: string;
  lastUpdated?: string;
  onToggleSidebar: () => void;
}

const MenuIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 12h18M3 6h18M3 18h18" />
  </svg>
);

// X/Twitter Icon
const XIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

export default function Header({
  currentTime,
  lastUpdated,
  onToggleSidebar,
}: HeaderProps) {
  const { lang, setLang, t } = useI18n();

  return (
    <header className="header">
      <div className="header-left">
        {/* Mobile menu toggle */}
        <button className="header-toggle" onClick={onToggleSidebar}>
          <MenuIcon />
        </button>

        {/* Page title for mobile */}
        <span className="header-title">{t("page.trending")}</span>
      </div>

      <div className="header-right">
        {/* Time display - hidden on very small screens */}
        <div className="header-time hide-mobile-sm">
          <div>{currentTime}</div>
          {lastUpdated && (
            <div style={{ opacity: 0.7 }}>{lastUpdated}</div>
          )}
        </div>

        {/* Twitter/X Follow Button */}
        <a
          href="https://x.com/ohxiyu"
          target="_blank"
          rel="noopener noreferrer"
          className="twitter-btn"
          title={t("header.followTwitter")}
        >
          <XIcon />
          <span className="twitter-btn-text">{t("header.followTwitter")}</span>
        </a>

        {/* Language toggle pill */}
        <div className="lang-toggle">
          <button
            className={`lang-toggle-btn ${lang === "en" ? "active" : ""}`}
            onClick={() => setLang("en")}
          >
            {t("header.langEn")}
          </button>
          <button
            className={`lang-toggle-btn ${lang === "zh" ? "active" : ""}`}
            onClick={() => setLang("zh")}
          >
            {t("header.langZh")}
          </button>
        </div>
      </div>
    </header>
  );
}
