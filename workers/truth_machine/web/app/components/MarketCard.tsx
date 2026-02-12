"use client";

import { cn } from "../lib/utils";
import { useI18n } from "../hooks/useI18n";

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

interface MarketCardProps {
  item: MarketItem;
  density: Density;
}

export default function MarketCard({ item, density }: MarketCardProps) {
  const { t, formatMoney, formatPercent } = useI18n();

  // Check if we have valid odds to display
  const hasOdds = item.yes !== null && item.yes !== undefined;

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="market-card"
    >
      {/* Header: Rank + Title */}
      <div className="market-card-header">
        <div className={cn("market-card-rank", item.rank <= 3 && "top-3")}>
          {item.rank}
        </div>
        <h3 className="market-card-title">{item.title}</h3>
      </div>

      {/* Odds - only show if we have valid yes/no values */}
      {hasOdds && (
        <div className="market-card-odds">
          <div className="market-card-odd-item">
            <span className="market-card-odd-label">{t("card.yes")}</span>
            <span className="market-card-odd-value yes tabular-nums">
              {formatPercent(item.yes!)}
            </span>
          </div>
          {item.no !== null && (
            <div className="market-card-odd-item">
              <span className="market-card-odd-label">{t("card.no")}</span>
              <span className="market-card-odd-value no tabular-nums">
                {formatPercent(item.no)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Meta: Volume & Liquidity */}
      <div className="market-card-meta">
        {item.volume_24h !== null && item.volume_24h !== undefined && (
          <div className="market-card-meta-item">
            <span>{t("card.volume")}:</span>
            <span className="tabular-nums">{formatMoney(item.volume_24h)}</span>
          </div>
        )}
        {item.liquidity !== null && item.liquidity !== undefined && (
          <div className="market-card-meta-item">
            <span>{t("card.liquidity")}:</span>
            <span className="tabular-nums">{formatMoney(item.liquidity)}</span>
          </div>
        )}
      </div>

      {/* AI Summary */}
      {item.summary && (
        <p className={cn("market-card-summary", density)}>
          {item.summary}
        </p>
      )}
    </a>
  );
}
