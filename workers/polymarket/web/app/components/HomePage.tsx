"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useI18n } from "../hooks/useI18n";
import { formatUTCTime } from "../lib/utils";

import Sidebar from "./Sidebar";
import Header from "./Header";
import TrendingRow from "./TrendingRow";
import TabsBar, { PlatformInfo } from "./TabsBar";
import MarketGrid from "./MarketGrid";
import Skeleton, { TrendingSkeleton } from "./Skeleton";
import { ToastContainer, useToast } from "./Toast";

type ViewMode = "grid" | "list";
type Density = "compact" | "full";

interface MarketItem {
  rank: number;
  market_id: string;
  title: string;
  yes: number | null;
  no: number | null;
  volume_24h: number | null;
  liquidity: number | null;
  url: string;
  summary: string | null;
}

interface Report {
  platform: string;
  updated_at: string;
  title: string;
  items: MarketItem[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";
const REFRESH_INTERVAL = 60000; // 60 seconds
const PLATFORM_STORAGE_KEY = "qwe_platform";
const DEFAULT_PLATFORM = "opinion"; // Opinion as default

// Platform priority order for sorting
const PLATFORM_ORDER: string[] = [
  "opinion",
  "polymarket",
  "limitless",
  "kalshi",
  // Others will be sorted alphabetically after these
];

/**
 * Sort platforms by priority order
 */
function sortPlatforms(platforms: PlatformInfo[]): PlatformInfo[] {
  return [...platforms].sort((a, b) => {
    const aIndex = PLATFORM_ORDER.indexOf(a.id);
    const bIndex = PLATFORM_ORDER.indexOf(b.id);

    // If both are in priority list, sort by priority
    if (aIndex !== -1 && bIndex !== -1) {
      return aIndex - bIndex;
    }
    // If only a is in priority list, a comes first
    if (aIndex !== -1) return -1;
    // If only b is in priority list, b comes first
    if (bIndex !== -1) return 1;
    // Otherwise sort alphabetically
    return a.name.localeCompare(b.name);
  });
}

/**
 * Fetch list of available platforms from API
 */
async function fetchPlatforms(): Promise<PlatformInfo[]> {
  try {
    const response = await fetch(`${API_BASE}/v1/platforms`);
    if (!response.ok) {
      console.warn("Failed to fetch platforms, using defaults");
      return [{ id: "polymarket", name: "Polymarket", enabled: true }];
    }
    const data = await response.json();
    return data.filter((p: PlatformInfo) => p.enabled);
  } catch (error) {
    console.warn("Failed to fetch platforms:", error);
    return [{ id: "polymarket", name: "Polymarket", enabled: true }];
  }
}

/**
 * Fetch report for a specific platform
 * @param platform - Platform ID
 * @param lang - Language for AI summaries (zh or en)
 * @param limit - Maximum number of markets to fetch (default 20)
 */
async function fetchReport(platform: string, lang: string = "zh", limit: number = 20): Promise<Report> {
  const response = await fetch(`${API_BASE}/v1/reports/latest?platform=${platform}&lang=${lang}&limit=${limit}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get initial platform from URL, localStorage, or default
 */
function getInitialPlatform(
  searchParams: URLSearchParams,
  availablePlatforms: string[]
): string {
  // 1. URL query parameter has highest priority
  const urlPlatform = searchParams.get("platform");
  if (urlPlatform && availablePlatforms.includes(urlPlatform)) {
    return urlPlatform;
  }

  // 2. localStorage
  if (typeof window !== "undefined") {
    const storedPlatform = localStorage.getItem(PLATFORM_STORAGE_KEY);
    if (storedPlatform && availablePlatforms.includes(storedPlatform)) {
      return storedPlatform;
    }
  }

  // 3. Default: polymarket if available, otherwise first platform
  if (availablePlatforms.includes(DEFAULT_PLATFORM)) {
    return DEFAULT_PLATFORM;
  }
  return availablePlatforms[0] || DEFAULT_PLATFORM;
}

export default function HomePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t, getRelativeTime, lang } = useI18n();

  // Platforms state
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [platformsLoading, setPlatformsLoading] = useState(true);

  // Selected platform
  const [selectedPlatform, setSelectedPlatform] = useState<string>(DEFAULT_PLATFORM);

  // View settings
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [density, setDensity] = useState<Density>("compact");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Report state
  const [report, setReport] = useState<Report | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");

  const { toasts, removeToast, error: showError } = useToast();

  // Refs to avoid dependency issues
  const showErrorRef = useRef(showError);
  showErrorRef.current = showError;

  // Update UTC time every second
  useEffect(() => {
    const updateTime = () => setCurrentTime(formatUTCTime());
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Load platforms on mount
  useEffect(() => {
    const loadPlatforms = async () => {
      setPlatformsLoading(true);
      const platformsList = await fetchPlatforms();
      // Sort platforms: Opinion first, then Polymarket, then others
      const sortedPlatforms = sortPlatforms(platformsList);
      setPlatforms(sortedPlatforms);

      // Set initial platform based on URL/localStorage/default
      const platformIds = sortedPlatforms.map((p) => p.id);
      const initial = getInitialPlatform(searchParams, platformIds);
      setSelectedPlatform(initial);

      setPlatformsLoading(false);
    };

    loadPlatforms();
  }, [searchParams]);

  // Fetch report when platform or language changes
  const loadReport = useCallback(
    async (isInitial = false) => {
      if (!selectedPlatform) return;

      try {
        if (isInitial) {
          setInitialLoading(true);
        }
        setError(null);

        // Pass current language to API for AI summary localization
        const data = await fetchReport(selectedPlatform, lang);
        setReport(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to fetch data";
        setError(message);
        showErrorRef.current(message);
      } finally {
        if (isInitial) {
          setInitialLoading(false);
        }
      }
    },
    [selectedPlatform, lang]
  );

  // Load report when platform or language changes
  useEffect(() => {
    if (!platformsLoading && selectedPlatform) {
      loadReport(true);
    }
  }, [platformsLoading, selectedPlatform, lang, loadReport]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || platformsLoading) return;
    const timer = setInterval(() => loadReport(false), REFRESH_INTERVAL);
    return () => clearInterval(timer);
  }, [autoRefresh, platformsLoading, loadReport]);

  // Handle platform change
  const handlePlatformChange = useCallback(
    (platformId: string) => {
      setSelectedPlatform(platformId);

      // Persist to localStorage
      if (typeof window !== "undefined") {
        localStorage.setItem(PLATFORM_STORAGE_KEY, platformId);
      }

      // Update URL (replace, not push)
      const url = new URL(window.location.href);
      url.searchParams.set("platform", platformId);
      router.replace(url.pathname + url.search);
    },
    [router]
  );

  // Handlers
  const handleToggleSidebar = () => {
    if (typeof window !== "undefined" && window.innerWidth <= 640) {
      setMobileSidebarOpen((v) => !v);
    } else {
      setSidebarCollapsed((v) => !v);
    }
  };

  const handleRetry = () => {
    loadReport(true);
  };

  // Get current platform name for display
  const currentPlatformName =
    platforms.find((p) => p.id === selectedPlatform)?.name || selectedPlatform;

  // Items to display
  const filteredItems = report?.items || [];

  return (
    <div className={`app-layout ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        mobileOpen={mobileSidebarOpen}
        onToggleMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="main-wrapper">
        {/* Header */}
        <Header
          currentTime={currentTime}
          lastUpdated={report ? getRelativeTime(report.updated_at) : undefined}
          onToggleSidebar={handleToggleSidebar}
        />

        {/* Content Area */}
        <main className="main-content">
          {/* Page Title */}
          <div className="page-title" style={{ marginBottom: "var(--space-xl)" }}>
            <h1 style={{
              fontSize: "var(--text-xl)",
              fontWeight: "var(--weight-semibold)",
              color: "var(--text-primary)",
            }}>
              {t("page.trending")} · {currentPlatformName}
            </h1>
          </div>

          {/* Loading State */}
          {(initialLoading || platformsLoading) && !report && (
            <>
              <TrendingSkeleton />
              <Skeleton count={6} />
            </>
          )}

          {/* Error State */}
          {error && !initialLoading && (
            <div className="error-state">
              <svg
                className="error-state-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
              <h3 className="error-state-title">{t("state.error")}</h3>
              <p className="error-state-text">{error}</p>
              <button className="retry-btn" onClick={handleRetry}>
                {t("state.retry")}
              </button>
            </div>
          )}

          {/* Content */}
          {!initialLoading && !platformsLoading && !error && report && (
            <>
              {/* Trending Row - only show if there are items */}
              {filteredItems.length > 0 && <TrendingRow items={filteredItems} />}

              {/* Tabs Bar - Always show so users can switch platforms */}
              <TabsBar
                platforms={platforms}
                selectedPlatform={selectedPlatform}
                viewMode={viewMode}
                density={density}
                autoRefresh={autoRefresh}
                onPlatformChange={handlePlatformChange}
                onViewModeChange={setViewMode}
                onDensityChange={setDensity}
                onAutoRefreshChange={setAutoRefresh}
              />

              {/* Empty State - when platform has no data yet */}
              {filteredItems.length === 0 && (
                <div className="empty-state" style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "var(--space-3xl) var(--space-xl)",
                  textAlign: "center",
                  color: "var(--text-secondary)"
                }}>
                  <svg
                    width="64"
                    height="64"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1"
                    style={{ marginBottom: "var(--space-lg)", opacity: 0.5 }}
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <path d="M3 9h18M9 21V9" />
                  </svg>
                  <h3 style={{
                    fontSize: "var(--text-lg)",
                    fontWeight: "var(--weight-semibold)",
                    color: "var(--text-primary)",
                    marginBottom: "var(--space-sm)"
                  }}>
                    {t("state.empty")}
                  </h3>
                  <p style={{ marginBottom: "var(--space-lg)" }}>
                    {t("state.emptyDesc")}
                  </p>
                </div>
              )}

              {/* Market Grid - only show if there are items */}
              {filteredItems.length > 0 && (
                <MarketGrid items={filteredItems} viewMode={viewMode} density={density} />
              )}
            </>
          )}
        </main>

        {/* Footer */}
        <footer
          style={{
            borderTop: "1px solid var(--border-light)",
            padding: "var(--space-lg) var(--space-xl)",
            textAlign: "center",
            fontSize: "var(--text-xs)",
            color: "var(--text-tertiary)",
          }}
        >
          {t("footer.text")}
        </footer>
      </div>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
