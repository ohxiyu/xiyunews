"use client";

interface SkeletonCardProps {
  count?: number;
}

function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-text" />
      <div className="skeleton skeleton-text" style={{ width: "40%" }} />
      <div className="skeleton skeleton-small" />
    </div>
  );
}

export default function Skeleton({ count = 6 }: SkeletonCardProps) {
  return (
    <div className="market-grid">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function TrendingSkeleton() {
  return (
    <section className="trending-section">
      <div className="trending-header">
        <div className="skeleton" style={{ width: 120, height: 20 }} />
      </div>
      <div className="trending-scroll">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="trending-card" style={{ opacity: 0.5 }}>
            <div className="skeleton" style={{ width: 30, height: 14, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: "100%", height: 32, marginBottom: 8 }} />
            <div className="skeleton" style={{ width: 80, height: 16 }} />
          </div>
        ))}
      </div>
    </section>
  );
}
