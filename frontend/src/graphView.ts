import type { GraphView } from "./types";

export interface GraphElement {
  data: Record<string, string | number | undefined>;
  classes?: string;
}

const DEFAULT_RELATIONS = new Set(["triggers", "escalates", "justifies", "disrupts"]);

export function causalSpineElements(graph: GraphView): GraphElement[] {
  const edges = graph.edges.filter((edge) => DEFAULT_RELATIONS.has(edge.relation));
  const nodes = graph.nodes;

  return [
    ...nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.node_type,
        confidence: node.confidence,
        sourceCount: node.source_count
      },
      classes: `node-${node.node_type} confidence-${node.confidence}`
    })),
    ...edges.map((edge) => ({
      data: {
        id: edge.id,
        source: edge.source_node_id,
        target: edge.target_node_id,
        label: edge.relation,
        confidence: edge.confidence,
        claimType: edge.claim_type
      },
      classes: `edge-${edge.relation} confidence-${edge.confidence}`
    }))
  ];
}

export function highlightedNeighborhood(graph: GraphView, selectedNodeId: string | null): Set<string> {
  if (!selectedNodeId) {
    return new Set();
  }
  const highlighted = new Set<string>([selectedNodeId]);
  for (const edge of graph.edges) {
    if (edge.source_node_id === selectedNodeId || edge.target_node_id === selectedNodeId) {
      highlighted.add(edge.id);
      highlighted.add(edge.source_node_id);
      highlighted.add(edge.target_node_id);
    }
  }
  return highlighted;
}
