"use client";

import MarketCard from "./MarketCard";
import { cn } from "../lib/utils";
import { useI18n } from "../hooks/useI18n";

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

interface MarketGridProps {
  items: MarketItem[];
  viewMode: ViewMode;
  density: Density;
}

export default function MarketGrid({ items, viewMode, density }: MarketGridProps) {
  const { t } = useI18n();

  if (items.length === 0) {
    return (
      <div className="empty-state">
        <svg className="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        <h3 className="empty-state-title">{t("state.noData")}</h3>
        <p className="empty-state-text">
          {t("state.noData")}
        </p>
      </div>
    );
  }

  return (
    <div className={cn("market-grid", viewMode === "list" && "list-view")}>
      {items.map((item) => (
        <MarketCard
          key={item.market_id}
          item={item}
          density={density}
        />
      ))}
    </div>
  );
}
