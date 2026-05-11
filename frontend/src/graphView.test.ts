import { describe, expect, it } from "vitest";

import { causalSpineElements, highlightedNeighborhood } from "./graphView";
import type { GraphView } from "./types";

const graph: GraphView = {
  view: "spine",
  nodes: [
    { id: "a", label: "A", node_type: "strategic_driver", summary: "", source_ids: [], claim_cluster_ids: [], confidence: "medium", claim_type: "reported_fact", source_count: 1 },
    { id: "b", label: "B", node_type: "proximate_trigger", summary: "", source_ids: [], claim_cluster_ids: [], confidence: "medium", claim_type: "reported_fact", source_count: 1 },
    { id: "c", label: "C", node_type: "market_reaction", summary: "", source_ids: [], claim_cluster_ids: [], confidence: "low", claim_type: "market_expectation", source_count: 1 }
  ],
  edges: [
    { id: "ab", source_node_id: "a", target_node_id: "b", relation: "triggers", summary: "", source_ids: [], claim_cluster_ids: [], confidence: "medium", claim_type: "reported_fact" },
    { id: "bc", source_node_id: "b", target_node_id: "c", relation: "correlates_with", summary: "", source_ids: [], claim_cluster_ids: [], confidence: "low", claim_type: "market_expectation" }
  ]
};

describe("causalSpineElements", () => {
  it("omits correlates_with edges from the default spine view", () => {
    const elements = causalSpineElements(graph);

    expect(elements.some((element) => element.data.id === "bc")).toBe(false);
    expect(elements.some((element) => element.data.id === "ab")).toBe(true);
  });

  it("keeps evidence-map nodes visible even when default causal edges are absent", () => {
    const elements = causalSpineElements({ ...graph, edges: [] });

    expect(elements.map((element) => element.data.id)).toEqual(["a", "b", "c"]);
  });
});

describe("highlightedNeighborhood", () => {
  it("returns the selected node and its directly connected nodes", () => {
    const ids = highlightedNeighborhood(graph, "b");

    expect(ids).toEqual(new Set(["a", "b", "c", "ab", "bc"]));
  });
});
