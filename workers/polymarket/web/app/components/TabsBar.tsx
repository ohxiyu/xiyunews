"use client";

import { cn } from "../lib/utils";
import { useI18n } from "../hooks/useI18n";

type ViewMode = "grid" | "list";
type Density = "compact" | "full";

export interface PlatformInfo {
  id: string;
  name: string;
  enabled: boolean;
}

interface TabsBarProps {
  platforms: PlatformInfo[];
  selectedPlatform: string;
  viewMode: ViewMode;
  density: Density;
  autoRefresh: boolean;
  onPlatformChange: (platformId: string) => void;
  onViewModeChange: (v: ViewMode) => void;
  onDensityChange: (d: Density) => void;
  onAutoRefreshChange: (v: boolean) => void;
}

export default function TabsBar({
  platforms,
  selectedPlatform,
  viewMode,
  density,
  autoRefresh,
  onPlatformChange,
  onViewModeChange,
  onDensityChange,
  onAutoRefreshChange,
}: TabsBarProps) {
  const { t } = useI18n();

  return (
    <div className="tabs-bar">
      <div className="tabs-left">
        {platforms.map((platform) => (
          <button
            key={platform.id}
            className={cn("tab-item", selectedPlatform === platform.id && "active")}
            onClick={() => onPlatformChange(platform.id)}
          >
            {platform.name}
          </button>
        ))}
      </div>

      <div className="tabs-right">
        {/* View mode toggle */}
        <div className="view-toggle">
          <button
            className={cn("view-toggle-btn", viewMode === "grid" && "active")}
            onClick={() => onViewModeChange("grid")}
          >
            {t("view.grid")}
          </button>
          <button
            className={cn("view-toggle-btn", viewMode === "list" && "active")}
            onClick={() => onViewModeChange("list")}
          >
            {t("view.list")}
          </button>
        </div>

        {/* Density toggle */}
        <div className="density-toggle">
          <button
            className={cn("density-toggle-btn", density === "compact" && "active")}
            onClick={() => onDensityChange("compact")}
          >
            {t("view.compact")}
          </button>
          <button
            className={cn("density-toggle-btn", density === "full" && "active")}
            onClick={() => onDensityChange("full")}
          >
            {t("view.full")}
          </button>
        </div>

        {/* Auto refresh */}
        <label className="auto-refresh">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => onAutoRefreshChange(e.target.checked)}
          />
          <span>{t("controls.autoRefresh")}</span>
        </label>
      </div>
    </div>
  );
}
