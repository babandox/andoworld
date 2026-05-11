import type { MarketMarker, MarketSeriesPoint, TensionSeriesPoint, TimelineEvent } from "./types";

export interface IndexedMarketSeriesPoint extends MarketSeriesPoint {
  indexedValue: number;
  percentChange: number;
}

export interface MarketEventOverlay {
  id: string;
  kind: "timeline" | "marker";
  date: string;
  title: string;
  summary: string;
  category: TimelineEvent["category"] | MarketMarker["marker_type"];
  sourceCount: number;
  sourceIds: string[];
}

export interface EventRugItem {
  date: string;
  title: string;
  category: string;
  count: number;
  overlays: MarketEventOverlay[];
}

export type ChartWindowMode = "full" | "war" | "selected";
export interface ChartWindow {
  start: string;
  end: string;
}

export function groupSeries(points: MarketSeriesPoint[]): Map<string, MarketSeriesPoint[]> {
  const grouped = new Map<string, MarketSeriesPoint[]>();
  for (const point of points) {
    const values = grouped.get(point.series) ?? [];
    values.push(point);
    grouped.set(point.series, values);
  }
  for (const values of grouped.values()) {
    values.sort((left, right) => left.date.localeCompare(right.date));
  }
  return grouped;
}

export function percentMove(previous: number, next: number): string {
  const percent = ((next - previous) / previous) * 100;
  const sign = percent >= 0 ? "+" : "";
  return `${sign}${percent.toFixed(1)}%`;
}

export function indexSeriesToBaseline(points: MarketSeriesPoint[]): Map<string, IndexedMarketSeriesPoint[]> {
  const grouped = groupSeries(points);
  const indexed = new Map<string, IndexedMarketSeriesPoint[]>();
  for (const [series, values] of grouped) {
    const baseline = values[0]?.value;
    if (!baseline) {
      indexed.set(series, []);
      continue;
    }
    indexed.set(
      series,
      values.map((point) => {
        const rawIndex = (point.value / baseline) * 100;
        return {
          ...point,
          indexedValue: round(rawIndex),
          percentChange: round(rawIndex - 100)
        };
      })
    );
  }
  return indexed;
}

export function buildMarketEventOverlays(events: TimelineEvent[], markers: MarketMarker[]): MarketEventOverlay[] {
  const timelineOverlays: MarketEventOverlay[] = events
    .filter((event) => event.category !== "background" && isIsoDate(event.occurred_at))
    .map((event) => ({
      id: event.id,
      kind: "timeline",
      date: event.occurred_at,
      title: event.title,
      summary: event.summary,
      category: event.category,
      sourceCount: event.source_ids.length,
      sourceIds: event.source_ids
    }));

  const markerOverlays: MarketEventOverlay[] = markers
    .filter((marker) => isIsoDate(marker.occurred_at))
    .map((marker) => ({
      id: marker.id,
      kind: "marker",
      date: marker.occurred_at,
      title: marker.title,
      summary: marker.summary,
      category: marker.marker_type,
      sourceCount: marker.source_ids.length,
      sourceIds: marker.source_ids
    }));

  return [...timelineOverlays, ...markerOverlays].sort((left, right) => left.date.localeCompare(right.date));
}

export function buildEventRug(overlays: MarketEventOverlay[], mode: "major" | "all" = "major"): EventRugItem[] {
  const majorDates = new Set(overlays.filter((overlay) => isMajorOverlay(overlay)).map((overlay) => overlay.date.slice(0, 10)));
  const filtered = mode === "all" ? overlays : overlays.filter((overlay) => majorDates.has(overlay.date.slice(0, 10)));
  const grouped = new Map<string, MarketEventOverlay[]>();
  for (const overlay of filtered) {
    const date = overlay.date.slice(0, 10);
    grouped.set(date, [...(grouped.get(date) ?? []), overlay]);
  }
  return [...grouped.entries()]
    .map(([date, values]) => {
      const sorted = [...values].sort((left, right) => categoryWeight(right.category) - categoryWeight(left.category));
      const primary = sorted[0];
      return {
        date,
        title: primary.title,
        category: String(primary.category),
        count: sorted.length,
        overlays: sorted
      };
    })
    .sort((left, right) => left.date.localeCompare(right.date));
}

export function chartWindowForMode(
  mode: ChartWindowMode,
  points: MarketSeriesPoint[],
  overlays: MarketEventOverlay[],
  selectedDate?: string | null
): ChartWindow {
  const dates = [...new Set(points.map((point) => point.date))].sort();
  const fullStart = dates[0] ?? "";
  const fullEnd = dates[dates.length - 1] ?? "";
  if (!fullStart || !fullEnd || mode === "full") {
    return { start: fullStart, end: fullEnd };
  }

  if (mode === "selected" && selectedDate) {
    return clampWindow(addDays(selectedDate, -14), addDays(selectedDate, 14), fullStart, fullEnd);
  }

  const firstWarOverlay =
    overlays.find((overlay) => ["strike", "statement", "market", "market_move", "impact", "current_state"].includes(String(overlay.category))) ??
    overlays[0];
  return { start: firstWarOverlay?.date.slice(0, 10) ?? fullStart, end: fullEnd };
}

export function filterTensionSeriesForWindow(points: TensionSeriesPoint[], window: ChartWindow): TensionSeriesPoint[] {
  return points.filter((point) => point.date >= window.start && point.date <= window.end);
}

function isIsoDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}/.test(value);
}

function round(value: number): number {
  return Number(value.toFixed(2));
}

function isMajorOverlay(overlay: MarketEventOverlay): boolean {
  return overlay.kind === "marker" || categoryWeight(overlay.category) >= 3 || overlay.sourceCount > 1;
}

function categoryWeight(category: MarketEventOverlay["category"]): number {
  switch (category) {
    case "strike":
      return 6;
    case "statement":
      return 5;
    case "market":
    case "market_move":
    case "impact":
      return 4;
    case "diplomacy":
    case "current_state":
      return 3;
    case "prelude":
      return 2;
    default:
      return 1;
  }
}

function addDays(date: string, days: number): string {
  const value = new Date(`${date.slice(0, 10)}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

function clampWindow(start: string, end: string, min: string, max: string): ChartWindow {
  return {
    start: start < min ? min : start,
    end: end > max ? max : end
  };
}
