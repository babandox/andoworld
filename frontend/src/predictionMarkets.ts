import type { PredictionMarketPricePoint } from "./types";

export interface PredictionMarketSeries {
  marketId: string;
  question: string;
  outcome: string;
  status: PredictionMarketPricePoint["status"];
  marketStart?: string | null;
  marketEnd?: string | null;
  url?: string | null;
  points: PredictionMarketPricePoint[];
}

export interface PredictionMarketSections {
  active: PredictionMarketSeries[];
  resolved: PredictionMarketSeries[];
}

export interface PredictionMarketSplitOptions {
  activeLimit?: number;
  resolvedLimit?: number;
}

export function groupPredictionMarkets(points: PredictionMarketPricePoint[]): PredictionMarketSeries[] {
  const grouped = new Map<string, PredictionMarketPricePoint[]>();
  for (const point of points) {
    grouped.set(point.market_id, [...(grouped.get(point.market_id) ?? []), point]);
  }

  return [...grouped.entries()].map(([marketId, values]) => {
    const sorted = [...values].sort((left, right) => left.date.localeCompare(right.date));
    const first = sorted[0];
    const last = sorted[sorted.length - 1] ?? first;
    return {
      marketId,
      question: first?.question ?? marketId,
      outcome: first?.outcome ?? "Yes",
      status: last?.status ?? "active",
      marketStart: first?.market_start,
      marketEnd: last?.market_end,
      url: first?.url,
      points: sorted
    };
  });
}

export function sortPredictionMarkets(markets: PredictionMarketSeries[]): PredictionMarketSeries[] {
  return [...markets].sort((left, right) => {
    const statusDiff = statusWeight(right.status) - statusWeight(left.status);
    if (statusDiff !== 0) {
      return statusDiff;
    }
    return latestDate(right).localeCompare(latestDate(left));
  });
}

export function splitPredictionMarkets(markets: PredictionMarketSeries[], options: PredictionMarketSplitOptions = {}): PredictionMarketSections {
  const activeLimit = options.activeLimit ?? 8;
  const resolvedLimit = options.resolvedLimit ?? 24;
  const sorted = sortPredictionMarkets(markets);
  return {
    active: sorted.filter((market) => market.status === "active").slice(0, activeLimit),
    resolved: sorted.filter((market) => market.status !== "active").slice(0, resolvedLimit)
  };
}

export function latestProbability(market?: PredictionMarketSeries): string {
  const latest = market?.points[market.points.length - 1];
  if (!latest) {
    return "n/a";
  }
  return `${(latest.probability * 100).toFixed(latest.probability < 0.01 ? 1 : 0)}%`;
}

export function marketDateRange(market: PredictionMarketSeries): string {
  const first = market.marketStart ?? market.points[0]?.date;
  const last = market.marketEnd ?? market.points[market.points.length - 1]?.date;
  if (first && last) {
    return `${first} to ${last}`;
  }
  return first ?? last ?? "No dated closes";
}

function latestDate(market: PredictionMarketSeries): string {
  return market.points[market.points.length - 1]?.date ?? "";
}

function statusWeight(status: PredictionMarketPricePoint["status"]): number {
  if (status === "active") {
    return 2;
  }
  if (status === "closed") {
    return 1;
  }
  return 0;
}
