"use client";

import { cn } from "../lib/utils";
import { useI18n } from "../hooks/useI18n";

interface SidebarProps {
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleMobile: () => void;
}

const TrendingIcon = () => (
  <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
);

export default function Sidebar({ mobileOpen, onToggleMobile }: SidebarProps) {
  const { t } = useI18n();

  return (
    <>
      <aside className={cn("sidebar", mobileOpen && "open")}>
        {/* Logo */}
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">Q</div>
            <span className="sidebar-logo-text">Qwe</span>
          </div>
        </div>

        {/* Navigation - Only Trending */}
        <nav className="sidebar-nav">
          <a href="#" className="sidebar-nav-item active">
            <TrendingIcon />
            <span>{t("sidebar.trending")}</span>
          </a>
        </nav>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="sidebar-overlay" onClick={onToggleMobile} />
      )}
    </>
  );
}
