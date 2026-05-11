import { describe, expect, it } from "vitest";

import {
  filterTensionSeriesForWindow,
  buildEventRug,
  buildMarketEventOverlays,
  chartWindowForMode,
  groupSeries,
  indexSeriesToBaseline,
  percentMove
} from "./market";
import type { MarketMarker, MarketSeriesPoint, TensionSeriesPoint, TimelineEvent } from "./types";

const points: MarketSeriesPoint[] = [
  { series: "Brent", date: "2025-12-01", value: 73.4, source: "fixture" },
  { series: "Brent", date: "2026-02-28", value: 91.8, source: "fixture" },
  { series: "S&P 500", date: "2025-12-01", value: 6210, source: "fixture" }
];

describe("groupSeries", () => {
  it("groups market points by series name", () => {
    expect(groupSeries(points).get("Brent")?.length).toBe(2);
    expect(groupSeries(points).get("S&P 500")?.length).toBe(1);
  });
});

describe("percentMove", () => {
  it("formats percentage moves between two values", () => {
    expect(percentMove(73.4, 91.8)).toBe("+25.1%");
    expect(percentMove(91.8, 73.4)).toBe("-20.0%");
  });
});

describe("indexSeriesToBaseline", () => {
  it("normalizes each series to 100 at its first observation", () => {
    const indexed = indexSeriesToBaseline(points);

    expect(indexed.get("Brent")?.map((point) => point.indexedValue)).toEqual([100, 125.07]);
    expect(indexed.get("S&P 500")?.map((point) => point.indexedValue)).toEqual([100]);
  });
});

describe("buildMarketEventOverlays", () => {
  it("returns dated non-background timeline events before market freshness markers", () => {
    const events: TimelineEvent[] = [
      {
        id: "background",
        occurred_at: "2025-12-01",
        title: "Background anchor",
        summary: "Long-run context.",
        category: "background",
        source_ids: ["wiki:1"],
        claim_cluster_ids: [],
        confidence: "medium",
        claim_type: "actor_stated_rationale"
      },
      {
        id: "news",
        occurred_at: "2026-02-28",
        title: "Opening strike report",
        summary: "Dated report.",
        category: "strike",
        source_ids: ["gdelt:1", "wiki:1"],
        claim_cluster_ids: [],
        confidence: "high",
        claim_type: "reported_fact"
      }
    ];
    const markers: MarketMarker[] = [
      {
        id: "marker:fred",
        occurred_at: "2026-05-04",
        marker_type: "market_move",
        title: "Latest FRED market data",
        summary: "Freshness marker.",
        source_ids: ["fred:1"],
        related_node_ids: []
      }
    ];

    const overlays = buildMarketEventOverlays(events, markers);

    expect(overlays.map((overlay) => overlay.id)).toEqual(["news", "marker:fred"]);
    expect(overlays[0]).toMatchObject({ date: "2026-02-28", sourceCount: 2, kind: "timeline" });
    expect(overlays[1]).toMatchObject({ date: "2026-05-04", kind: "marker" });
  });
});

describe("buildEventRug", () => {
  it("groups multiple overlays on the same date and prioritizes higher-signal categories", () => {
    const overlays = [
      {
        id: "news",
        kind: "timeline" as const,
        date: "2026-02-28",
        title: "News report",
        summary: "News.",
        category: "prelude" as const,
        sourceCount: 1,
        sourceIds: ["gdelt:1"]
      },
      {
        id: "strike",
        kind: "timeline" as const,
        date: "2026-02-28",
        title: "Opening strike",
        summary: "Strike.",
        category: "strike" as const,
        sourceCount: 2,
        sourceIds: ["gdelt:2", "wiki:1"]
      }
    ];

    const rug = buildEventRug(overlays);

    expect(rug).toHaveLength(1);
    expect(rug[0]).toMatchObject({ date: "2026-02-28", category: "strike", count: 2 });
    expect(rug[0].title).toBe("Opening strike");
  });
});

describe("chartWindowForMode", () => {
  it("uses the full market range by default", () => {
    expect(chartWindowForMode("full", points, [])).toEqual({ start: "2025-12-01", end: "2026-02-28" });
  });

  it("centers the selected-event view around the selected event", () => {
    expect(chartWindowForMode("selected", points, [], "2026-02-20")).toEqual({ start: "2026-02-06", end: "2026-02-28" });
  });
});

describe("filterTensionSeriesForWindow", () => {
  it("filters tension points to the active chart window", () => {
    const tension: TensionSeriesPoint[] = [
      { date: "2026-02-28", value: 50, source: "rule_based", source_ids: [], summary: "Before" },
      { date: "2026-03-01", value: 65, source: "rule_based", source_ids: ["wiki-ref:1"], summary: "Strike" },
      { date: "2026-03-03", value: 55, source: "rule_based", source_ids: [], summary: "Decay" }
    ];

    expect(filterTensionSeriesForWindow(tension, { start: "2026-03-01", end: "2026-03-02" }).map((point) => point.date)).toEqual(["2026-03-01"]);
  });
});
