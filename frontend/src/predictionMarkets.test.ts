import { describe, expect, it } from "vitest";

import { groupPredictionMarkets, latestProbability, marketDateRange, splitPredictionMarkets, sortPredictionMarkets } from "./predictionMarkets";
import type { PredictionMarketPricePoint } from "./types";

const points: PredictionMarketPricePoint[] = [
  {
    market_id: "oil",
    question: "Will WTI crude oil hit $90 by end of June?",
    token_id: "yes-oil",
    outcome: "Yes",
    date: "2026-04-01",
    probability: 0.22,
    status: "active",
    source: "Polymarket",
    market_start: "2026-03-28",
    market_end: "2026-06-30",
    url: "https://polymarket.com/event/oil"
  },
  {
    market_id: "iran",
    question: "US x Iran permanent peace deal by May 31, 2026?",
    token_id: "yes-iran",
    outcome: "Yes",
    date: "2026-04-08",
    probability: 0.125,
    status: "resolved",
    source: "Polymarket",
    market_start: "2026-04-08",
    market_end: "2026-04-23",
    url: "https://polymarket.com/event/iran"
  },
  {
    market_id: "iran",
    question: "US x Iran permanent peace deal by May 31, 2026?",
    token_id: "yes-iran",
    outcome: "Yes",
    date: "2026-04-22",
    probability: 0.0005,
    status: "resolved",
    source: "Polymarket",
    market_start: "2026-04-08",
    market_end: "2026-04-23",
    url: "https://polymarket.com/event/iran"
  }
];

describe("prediction market helpers", () => {
  it("groups daily probability points by market and sorts them by date", () => {
    const grouped = groupPredictionMarkets([...points].reverse());

    expect(grouped).toHaveLength(2);
    expect(grouped.find((market) => market.marketId === "iran")?.points.map((point) => point.date)).toEqual(["2026-04-08", "2026-04-22"]);
  });

  it("formats latest probability from the most recent daily close", () => {
    const iran = groupPredictionMarkets(points).find((market) => market.marketId === "iran");

    expect(latestProbability(iran)).toBe("0.1%");
  });

  it("uses the market open and close range when only one daily close is available", () => {
    const oil = groupPredictionMarkets(points).find((market) => market.marketId === "oil");

    expect(oil).toBeDefined();
    expect(oil ? marketDateRange(oil) : "").toBe("2026-03-28 to 2026-06-30");
  });

  it("sorts active markets before resolved markets, then by latest update", () => {
    const grouped = groupPredictionMarkets(points);

    expect(sortPredictionMarkets(grouped).map((market) => market.marketId)).toEqual(["oil", "iran"]);
  });

  it("splits active and resolved markets so resolved markets are never hidden by active caps", () => {
    const crowded = [
      ...Array.from({ length: 12 }, (_, index) => ({
        market_id: `active-${index}`,
        question: `Will WTI crude oil hit $${90 + index}?`,
        token_id: `yes-active-${index}`,
        outcome: "Yes",
        date: `2026-05-${String(index + 1).padStart(2, "0")}`,
        probability: 0.2,
        status: "active" as const,
        source: "Polymarket" as const
      })),
      {
        market_id: "resolved-march",
        question: "Will there be an Iran ceasefire by March 31?",
        token_id: "yes-resolved",
        outcome: "Yes",
        date: "2026-03-31",
        probability: 0,
        status: "resolved" as const,
        source: "Polymarket" as const
      }
    ];

    const sections = splitPredictionMarkets(groupPredictionMarkets(crowded), { activeLimit: 8, resolvedLimit: 8 });

    expect(sections.active).toHaveLength(8);
    expect(sections.resolved.map((market) => market.marketId)).toContain("resolved-march");
  });
});
