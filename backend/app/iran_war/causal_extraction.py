from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any
from urllib.request import Request, urlopen

from backend.app.iran_war.config import load_env_file
from backend.app.models import AtomicClaimRecord, ClaimClusterRecord, GraphEdge, GraphNode, GraphView, SourceDocument


DEFAULT_OPENAI_EXTRACTION_MODEL = "gpt-5.5"


ALLOWED_CLAIM_TYPES = {
    "reported_fact",
    "actor_stated_rationale",
    "contested_interpretation",
    "market_expectation",
    "model_inference",
}
CLAIM_TYPE_ALIASES = {
    "historical": "actor_stated_rationale",
    "historical_context": "actor_stated_rationale",
    "rationale": "actor_stated_rationale",
    "actor_rationale": "actor_stated_rationale",
    "analysis": "contested_interpretation",
    "interpretation": "contested_interpretation",
    "inference": "model_inference",
}


@dataclass
class CausalExtraction:
    graph_view: GraphView
    atomic_claims: list[AtomicClaimRecord]
    claim_clusters: list[ClaimClusterRecord]
    method: str
    model: str | None = None


def extract_causal_structure(source_documents: list[SourceDocument]) -> CausalExtraction | None:
    wikipedia_docs = [source for source in source_documents if source.source_type == "wikipedia"]
    if not wikipedia_docs:
        return None

    openai_result = _extract_with_openai_if_enabled(wikipedia_docs, source_documents)
    if openai_result:
        return openai_result
    return _extract_with_rules(wikipedia_docs, source_documents)


def _extract_with_openai_if_enabled(
    wikipedia_docs: list[SourceDocument],
    all_sources: list[SourceDocument],
) -> CausalExtraction | None:
    load_env_file()
    if os.getenv("IRAN_WAR_DISABLE_OPENAI_EXTRACTION", "").lower() in {"1", "true", "yes"}:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt_sources = wikipedia_docs[:12]
    source_block = "\n".join(
        f"SOURCE_ID: {source.id}\nTITLE: {source.title}\nSECTION: {source.section_title or ''}\nEXCERPT: {source.excerpt}\n"
        for source in prompt_sources
    )
    prompt = (
        "Extract a source-backed causal graph explaining what caused the 2026 Iran war. "
        "Use only the supplied Wikipedia sources. Return strict JSON with keys nodes and edges. "
        "Each node must have id, label, node_type, summary, source_ids, confidence, claim_type. "
        "Each edge must have id, source_node_id, target_node_id, relation, summary, source_ids, confidence, claim_type. "
        "Allowed node_type values: structural_driver, strategic_driver, proximate_trigger, actor_rationale, "
        "contested_interpretation, opening_event, impact, current_state. "
        "Allowed edge relation values: enables, pressures, justifies, triggers, escalates, constrains, disrupts. "
        "Do not include Polymarket or FRED as causal nodes.\n\n"
        f"{source_block}"
    )

    try:
        model = os.getenv("OPENAI_EXTRACTION_MODEL", DEFAULT_OPENAI_EXTRACTION_MODEL)
        payload = _build_openai_chat_payload(model=model, prompt=prompt)
        request = Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        content = response_payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return _coerce_openai_graph(parsed, all_sources, model=model)
    except Exception:
        return None


def _build_openai_chat_payload(model: str, prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You produce auditable JSON for geopolitical causal analysis."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    if not model.startswith("gpt-5"):
        payload["temperature"] = 0.1
    return payload


def _coerce_openai_graph(payload: dict[str, Any], all_sources: list[SourceDocument], model: str | None = None) -> CausalExtraction | None:
    source_ids = {source.id for source in all_sources}
    nodes: list[GraphNode] = []
    for item in payload.get("nodes", []):
        node_source_ids = [source_id for source_id in item.get("source_ids", []) if source_id in source_ids]
        if not node_source_ids:
            continue
        try:
            nodes.append(
                GraphNode(
                    id=_stable_node_id(str(item.get("id") or item.get("label"))),
                    label=str(item["label"]),
                    node_type=item["node_type"],
                    summary=str(item["summary"]),
                    source_ids=node_source_ids,
                    claim_cluster_ids=[],
                    confidence=_coerce_confidence(item.get("confidence", "medium")),
                    claim_type=_coerce_claim_type(item.get("claim_type", "actor_stated_rationale")),
                    source_count=len(node_source_ids),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue

    node_ids = {node.id for node in nodes}
    edges: list[GraphEdge] = []
    for item in payload.get("edges", []):
        source_node_id = _stable_node_id(str(item.get("source_node_id")))
        target_node_id = _stable_node_id(str(item.get("target_node_id")))
        edge_source_ids = [source_id for source_id in item.get("source_ids", []) if source_id in source_ids]
        if source_node_id not in node_ids or target_node_id not in node_ids or not edge_source_ids:
            continue
        try:
            edges.append(
                GraphEdge(
                    id=_stable_edge_id(source_node_id, target_node_id, str(item.get("relation", "pressures"))),
                    source_node_id=source_node_id,
                    target_node_id=target_node_id,
                    relation=item.get("relation", "pressures"),
                    summary=str(item.get("summary", "")),
                    source_ids=edge_source_ids,
                    claim_cluster_ids=[],
                    confidence=_coerce_confidence(item.get("confidence", "medium")),
                    claim_type=_coerce_claim_type(item.get("claim_type", "actor_stated_rationale")),
                )
            )
        except ValueError:
            continue

    if len(nodes) < 3:
        return None
    atomic_claims, claim_clusters = _claims_for_nodes(nodes)
    nodes = _attach_claim_ids(nodes, claim_clusters)
    edges = _attach_edge_claim_ids(edges, nodes)
    return CausalExtraction(GraphView(view="spine", nodes=nodes[:60], edges=edges), atomic_claims, claim_clusters, method="openai", model=model)


def _extract_with_rules(wikipedia_docs: list[SourceDocument], all_sources: list[SourceDocument]) -> CausalExtraction:
    gdelt_docs = [source for source in all_sources if source.source_type == "gdelt"]
    specs = [
        (
            "node:1953-coup",
            "1953 coup and long-run US-Iran distrust",
            "structural_driver",
            ["1953", "coup"],
            "Historical US and UK involvement in Iran's 1953 coup is treated as a long-run background driver of distrust.",
        ),
        (
            "node:1979-revolution",
            "1979 revolution and hostile state relationship",
            "structural_driver",
            ["1979", "revolution"],
            "The 1979 Iranian Revolution changed Iran's relationship with the United States and Israel and anchors later hostility.",
        ),
        (
            "node:sanctions-pressure",
            "Sanctions and maximum-pressure strategy",
            "strategic_driver",
            ["sanction", "maximum pressure"],
            "Sanctions and maximum-pressure policy shaped the strategic environment around Iran before the war.",
        ),
        (
            "node:nuclear-issue",
            "Iran nuclear issue and JCPOA collapse",
            "strategic_driver",
            ["nuclear", "jcpoa"],
            "Iran's nuclear program, the JCPOA, and the collapse of diplomatic constraints are central stated drivers.",
        ),
        (
            "node:regional-shadow-conflict",
            "Iran-Israel shadow conflict and regional escalation",
            "strategic_driver",
            ["iran-israel", "israel", "middle eastern crisis", "regional"],
            "Iran-Israel confrontation and the wider regional crisis created escalation pressure before the war.",
        ),
        (
            "node:stated-rationales",
            "US and Israeli stated rationales",
            "actor_rationale",
            ["rationale", "deterrence", "security"],
            "US and Israeli rationales framed the war around nuclear risk, deterrence, and regional security.",
        ),
        (
            "node:hormuz-energy-risk",
            "Strait of Hormuz and energy supply risk",
            "impact",
            ["hormuz", "energy", "oil"],
            "The war created energy-market risk because of threats to shipping and oil flows around the Strait of Hormuz.",
        ),
    ]

    nodes: list[GraphNode] = []
    for node_id, label, node_type, keywords, summary in specs:
        sources = _matching_sources(wikipedia_docs, keywords)
        if sources:
            nodes.append(_node(node_id, label, node_type, summary, sources))

    if not any(node.id == "node:nuclear-issue" for node in nodes):
        sources = wikipedia_docs[:2]
        nodes.append(
            _node(
                "node:nuclear-issue",
                "Iran nuclear issue and JCPOA collapse",
                "strategic_driver",
                "Wikipedia background identifies Iran's nuclear issue as a central driver requiring further analysis.",
                sources,
            )
        )

    if gdelt_docs:
        nodes.append(
            _node(
                "node:current-state",
                "Current state and recent escalation reporting",
                "current_state",
                "Recent GDELT reporting supports the current-state layer of the case, not the historical causal backbone.",
                gdelt_docs[:8],
                claim_type="reported_fact",
            )
        )

    edges = _rule_edges(nodes)
    atomic_claims, claim_clusters = _claims_for_nodes(nodes)
    nodes = _attach_claim_ids(nodes, claim_clusters)
    edges = _attach_edge_claim_ids(edges, nodes)
    return CausalExtraction(GraphView(view="spine", nodes=nodes[:60], edges=edges), atomic_claims, claim_clusters, method="deterministic-wikipedia-fallback")


def _matching_sources(sources: list[SourceDocument], keywords: list[str]) -> list[SourceDocument]:
    matches: list[SourceDocument] = []
    for source in sources:
        text = f"{source.title} {source.section_title or ''} {source.excerpt}".casefold()
        if any(keyword.casefold() in text for keyword in keywords):
            matches.append(source)
    return matches[:8]


def _node(
    id: str,
    label: str,
    node_type: str,
    summary: str,
    sources: list[SourceDocument],
    claim_type: str = "actor_stated_rationale",
) -> GraphNode:
    source_ids = [source.id for source in sources]
    return GraphNode(
        id=id,
        label=label,
        node_type=node_type,  # type: ignore[arg-type]
        summary=summary,
        source_ids=source_ids,
        claim_cluster_ids=[],
        confidence="medium",
        claim_type=claim_type,  # type: ignore[arg-type]
        source_count=len(source_ids),
    )


def _rule_edges(nodes: list[GraphNode]) -> list[GraphEdge]:
    node_ids = {node.id for node in nodes}
    source_ids_by_node = {node.id: node.source_ids for node in nodes}
    candidates = [
        ("node:1953-coup", "node:1979-revolution", "enables", "Long-run foreign-intervention memory precedes the post-1979 hostile relationship."),
        ("node:1979-revolution", "node:sanctions-pressure", "pressures", "Post-revolution hostility and sanctions became part of the strategic environment."),
        ("node:sanctions-pressure", "node:nuclear-issue", "pressures", "Sanctions and nuclear negotiations are linked in the background evidence."),
        ("node:nuclear-issue", "node:stated-rationales", "justifies", "The nuclear issue is a central stated rationale for war decisions."),
        ("node:regional-shadow-conflict", "node:stated-rationales", "pressures", "Regional escalation shaped the stated security rationale."),
        ("node:stated-rationales", "node:current-state", "triggers", "Stated rationales connect the background drivers to the current war state."),
        ("node:current-state", "node:hormuz-energy-risk", "disrupts", "Current escalation reporting is connected to energy and Hormuz risk."),
    ]
    edges: list[GraphEdge] = []
    for source, target, relation, summary in candidates:
        if source not in node_ids or target not in node_ids:
            continue
        source_ids = list(dict.fromkeys(source_ids_by_node[source] + source_ids_by_node[target]))
        edges.append(
            GraphEdge(
                id=_stable_edge_id(source, target, relation),
                source_node_id=source,
                target_node_id=target,
                relation=relation,  # type: ignore[arg-type]
                summary=summary,
                source_ids=source_ids,
                claim_cluster_ids=[],
                confidence="medium",
                claim_type="actor_stated_rationale",
            )
        )
    return edges


def _claims_for_nodes(nodes: list[GraphNode]) -> tuple[list[AtomicClaimRecord], list[ClaimClusterRecord]]:
    claims: list[AtomicClaimRecord] = []
    clusters: list[ClaimClusterRecord] = []
    for node in nodes:
        claim_id = f"claim:{node.id.removeprefix('node:')}"
        cluster_id = f"cluster:{node.id.removeprefix('node:')}"
        claims.append(
            AtomicClaimRecord(
                id=claim_id,
                subject=node.label,
                predicate="contributed_to",
                object="2026 Iran war causal context",
                occurred_at="2025-12-01",
                quote=node.summary,
                source_ids=node.source_ids,
                canonical_entity_ids=[],
                claim_type=node.claim_type,
            )
        )
        clusters.append(
            ClaimClusterRecord(
                id=cluster_id,
                claim_ids=[claim_id],
                status="accepted",
                summary=node.summary,
                canonical_entity_ids=[],
            )
        )
    return claims, clusters


def _attach_claim_ids(nodes: list[GraphNode], clusters: list[ClaimClusterRecord]) -> list[GraphNode]:
    cluster_by_index = {index: cluster.id for index, cluster in enumerate(clusters)}
    return [node.model_copy(update={"claim_cluster_ids": [cluster_by_index[index]]}) for index, node in enumerate(nodes)]


def _attach_edge_claim_ids(edges: list[GraphEdge], nodes: list[GraphNode]) -> list[GraphEdge]:
    cluster_ids_by_node = {node.id: node.claim_cluster_ids for node in nodes}
    updated: list[GraphEdge] = []
    for edge in edges:
        cluster_ids = list(dict.fromkeys(cluster_ids_by_node.get(edge.source_node_id, []) + cluster_ids_by_node.get(edge.target_node_id, [])))
        updated.append(edge.model_copy(update={"claim_cluster_ids": cluster_ids}))
    return updated


def _stable_node_id(value: str) -> str:
    raw = value.casefold().removeprefix("node:")
    normalized = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return f"node:{normalized}"


def _stable_edge_id(source_node_id: str, target_node_id: str, relation: str) -> str:
    raw = f"{source_node_id}-{relation}-{target_node_id}".replace("node:", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.casefold()).strip("-")
    return f"edge:{normalized}"


def _coerce_confidence(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value >= 0.75:
            return "high"
        if value >= 0.45:
            return "medium"
        return "low"
    normalized = str(value or "").casefold()
    if normalized in {"high", "medium", "low"}:
        return normalized
    if normalized in {"certain", "strong"}:
        return "high"
    if normalized in {"uncertain", "weak"}:
        return "low"
    return "medium"


def _coerce_claim_type(value: Any) -> str:
    normalized = str(value or "").casefold()
    if normalized in ALLOWED_CLAIM_TYPES:
        return normalized
    return CLAIM_TYPE_ALIASES.get(normalized, "actor_stated_rationale")
