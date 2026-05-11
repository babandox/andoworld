export type Confidence = "high" | "medium" | "low";
export type ClaimType =
  | "reported_fact"
  | "actor_stated_rationale"
  | "contested_interpretation"
  | "market_expectation"
  | "model_inference";

export interface SourceDocument {
  id: string;
  source_type: "wikipedia" | "wikipedia_reference" | "gdelt" | "polymarket" | "fred" | "statement_archive" | "fixture";
  title: string;
  url?: string | null;
  published_at?: string | null;
  retrieved_at: string;
  revision_id?: string | null;
  section_title?: string | null;
  excerpt: string;
}

export interface TimelineEvent {
  id: string;
  occurred_at: string;
  title: string;
  summary: string;
  category: "background" | "prelude" | "statement" | "strike" | "diplomacy" | "market" | "impact" | "current_state";
  source_ids: string[];
  claim_cluster_ids: string[];
  confidence: Confidence;
  claim_type: ClaimType;
}

export interface GraphNode {
  id: string;
  label: string;
  node_type:
    | "structural_driver"
    | "strategic_driver"
    | "proximate_trigger"
    | "actor_rationale"
    | "contested_interpretation"
    | "opening_event"
    | "impact"
    | "current_state"
    | "market_reaction"
    | "supernode";
  summary: string;
  source_ids: string[];
  claim_cluster_ids: string[];
  confidence: Confidence;
  claim_type: ClaimType;
  source_count: number;
}

export interface GraphEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relation:
    | "enables"
    | "pressures"
    | "justifies"
    | "triggers"
    | "escalates"
    | "constrains"
    | "contradicts"
    | "disrupts"
    | "correlates_with";
  summary: string;
  source_ids: string[];
  claim_cluster_ids: string[];
  confidence: Confidence;
  claim_type: ClaimType;
}

export interface GraphView {
  view: "spine" | "neighborhood" | "timeline" | "contradictions" | "full";
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ClaimClusterRecord {
  id: string;
  claim_ids: string[];
  status: "accepted" | "disputed" | "superseded" | "unresolved";
  summary: string;
  canonical_entity_ids: string[];
}

export interface ClaimContradictionRecord {
  id: string;
  source_claim_id: string;
  target_claim_id: string;
  relationship: "entails" | "contradicts" | "partially_overlaps" | "reversal" | "unrelated";
  confidence: Confidence;
  rationale: string;
}

export interface MarketSeriesPoint {
  series: "Brent" | "WTI" | "S&P 500";
  date: string;
  value: number;
  source: "FRED" | "fixture";
}

export interface TensionSeriesPoint {
  date: string;
  value: number;
  source: "rule_based";
  source_ids: string[];
  summary: string;
}

export interface PredictionMarketPricePoint {
  market_id: string;
  question: string;
  token_id: string;
  outcome: string;
  date: string;
  probability: number;
  status: "active" | "closed" | "resolved";
  source: "Polymarket";
  market_start?: string | null;
  market_end?: string | null;
  url?: string | null;
}

export interface MarketMarker {
  id: string;
  occurred_at: string;
  marker_type: "statement" | "strike" | "market_move" | "polymarket" | "diplomacy";
  title: string;
  summary: string;
  source_ids: string[];
  related_node_ids: string[];
}

export interface SourceHealth {
  configured: boolean;
  available: boolean;
  note: string;
}

export interface SourceStatus {
  wikipedia: SourceHealth;
  gdelt: SourceHealth;
  polymarket: SourceHealth;
  fred: SourceHealth;
  openai: SourceHealth;
  postgres: SourceHealth;
  qdrant: SourceHealth;
}

export interface ExtractionStatus {
  method: string;
  note: string;
  source_scope: string[];
  extracted_claim_clusters: number;
}

export interface IranWarCase {
  title: string;
  evidence_window_start: string;
  evidence_window_end: string;
  summary: string;
  timeline_events: TimelineEvent[];
  graph_view: GraphView;
  source_documents: SourceDocument[];
  claim_clusters: ClaimClusterRecord[];
  claim_contradictions: ClaimContradictionRecord[];
  market_series: MarketSeriesPoint[];
  tension_series: TensionSeriesPoint[];
  prediction_market_series: PredictionMarketPricePoint[];
  market_markers: MarketMarker[];
  source_status: SourceStatus;
  extraction_status: ExtractionStatus;
}

export interface ClaimsResponse {
  clusters: ClaimClusterRecord[];
  contradictions: ClaimContradictionRecord[];
}

export interface MarketSeriesResponse {
  series: MarketSeriesPoint[];
  markers: MarketMarker[];
  tension_series: TensionSeriesPoint[];
}
