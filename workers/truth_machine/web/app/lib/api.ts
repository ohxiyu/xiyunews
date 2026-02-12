/**
 * API types and fetch functions for QweTruthMachine
 *
 * Supported Platforms (7):
 * - polymarket, kalshi, limitless, prophetx, novig, sxbet, manifold
 */

export interface MarketItem {
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

export interface Report {
  platform: string;
  updated_at: string;
  title: string;
  items: MarketItem[];
}

export interface PlatformInfo {
  id: string;
  name: string;
  enabled: boolean;
  description?: string;
}

export type ViewMode = 'grid' | 'list';
export type Density = 'compact' | 'full';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';

/**
 * Fetch list of available platforms from API
 */
export async function fetchPlatforms(): Promise<PlatformInfo[]> {
  const response = await fetch(`${API_BASE}/v1/platforms`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  const data = await response.json();
  return data.filter((p: PlatformInfo) => p.enabled);
}

/**
 * Fetch latest report for a platform
 */
export async function fetchReport(platform: string): Promise<Report> {
  const response = await fetch(
    `${API_BASE}/v1/reports/latest?platform=${platform}`
  );

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}
