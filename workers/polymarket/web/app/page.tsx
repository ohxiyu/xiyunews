"use client";

import { Suspense } from "react";
import { I18nProvider } from "./components/I18nProvider";
import HomePage from "./components/HomePage";
import Skeleton, { TrendingSkeleton } from "./components/Skeleton";

// Loading fallback
function LoadingFallback() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">Q</div>
            <span className="sidebar-logo-text">Qwe</span>
          </div>
        </div>
      </aside>
      <div className="main-wrapper">
        <header className="header" />
        <main className="main-content">
          <TrendingSkeleton />
          <Skeleton count={6} />
        </main>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <I18nProvider>
        <HomePage />
      </I18nProvider>
    </Suspense>
  );
}
