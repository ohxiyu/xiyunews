"use client";

import { useRef } from "react";
import { useI18n } from "../hooks/useI18n";

interface MarketItem {
  rank: number;
  market_id: string;
  title: string;
  yes: number | null;
  no: number | null;
  url: string;
}

interface TrendingRowProps {
  items: MarketItem[];
}

const ChevronLeft = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M15 18l-6-6 6-6" />
  </svg>
);

const ChevronRight = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 18l6-6-6-6" />
  </svg>
);

export default function TrendingRow({ items }: TrendingRowProps) {
  const { t, formatPercent } = useI18n();
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: "left" | "right") => {
    if (!scrollRef.current) return;
    const scrollAmount = 220; // card width + gap
    scrollRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  };

  // Only show first 10 items in trending
  const trendingItems = items.slice(0, 10);

  if (trendingItems.length === 0) return null;

  return (
    <section className="trending-section">
      <div className="trending-header">
        <h2 className="trending-title">{t("page.trending")}</h2>
        <div className="trending-nav">
          <button
            className="trending-nav-btn"
            onClick={() => scroll("left")}
            aria-label="Scroll left"
          >
            <ChevronLeft />
          </button>
          <button
            className="trending-nav-btn"
            onClick={() => scroll("right")}
            aria-label="Scroll right"
          >
            <ChevronRight />
          </button>
        </div>
      </div>

      <div className="trending-scroll" ref={scrollRef}>
        {trendingItems.map((item) => (
          <a
            key={item.market_id}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="trending-card"
          >
            <div className="trending-card-rank">#{item.rank}</div>
            <div className="trending-card-title">{item.title}</div>
            {item.yes !== null && (
              <div className="trending-card-odds">
                <span className="trending-card-odd yes">
                  {t("card.yes")} {formatPercent(item.yes)}
                </span>
                {item.no !== null && (
                  <span className="trending-card-odd no">
                    {t("card.no")} {formatPercent(item.no)}
                  </span>
                )}
              </div>
            )}
          </a>
        ))}
      </div>
    </section>
  );
}
