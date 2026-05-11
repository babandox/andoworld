import type { ClaimsResponse, GraphView, IranWarCase, MarketSeriesResponse, PredictionMarketPricePoint, SourceDocument, SourceStatus } from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export function fetchIranWarCase(): Promise<IranWarCase> {
  return requestJson<IranWarCase>("/api/iran-war");
}

export function fetchGraphView(view = "spine", focusNodeId?: string): Promise<GraphView> {
  const params = new URLSearchParams({ view });
  if (focusNodeId) {
    params.set("focus_node_id", focusNodeId);
  }
  return requestJson<GraphView>(`/api/iran-war/graph?${params.toString()}`);
}

export function fetchClaims(): Promise<ClaimsResponse> {
  return requestJson<ClaimsResponse>("/api/iran-war/claims");
}

export function fetchSources(): Promise<SourceDocument[]> {
  return requestJson<SourceDocument[]>("/api/iran-war/sources");
}

export function fetchMarketSeries(): Promise<MarketSeriesResponse> {
  return requestJson<MarketSeriesResponse>("/api/iran-war/market-series");
}

export function fetchPredictionMarketSeries(): Promise<PredictionMarketPricePoint[]> {
  return requestJson<PredictionMarketPricePoint[]>("/api/iran-war/prediction-market-series");
}

export function fetchSourceStatus(): Promise<SourceStatus> {
  return requestJson<SourceStatus>("/api/iran-war/source-status");
}
