from __future__ import annotations

from backend.app.iran_war.fixtures import GRAPH_EDGES, GRAPH_NODES
from backend.app.models import GraphView


SPINE_RELATIONS = {"triggers", "escalates", "justifies", "disrupts"}


def build_graph_view(view: str = "spine", focus_node_id: str | None = None) -> GraphView:
    if view == "full":
        return GraphView(view="full", nodes=GRAPH_NODES, edges=GRAPH_EDGES)
    if view == "neighborhood" and focus_node_id:
        return _neighborhood(focus_node_id)
    if view == "contradictions":
        nodes = [node for node in GRAPH_NODES if node.id == "node:trump-reversals"]
        return GraphView(view="contradictions", nodes=nodes, edges=[])
    if view == "timeline":
        return GraphView(view="timeline", nodes=GRAPH_NODES, edges=GRAPH_EDGES)

    spine_edges = [edge for edge in GRAPH_EDGES if edge.relation in SPINE_RELATIONS]
    node_ids = {edge.source_node_id for edge in spine_edges} | {edge.target_node_id for edge in spine_edges}
    spine_nodes = [node for node in GRAPH_NODES if node.id in node_ids][:60]
    return GraphView(view="spine", nodes=spine_nodes, edges=spine_edges)


def _neighborhood(focus_node_id: str) -> GraphView:
    edges = [edge for edge in GRAPH_EDGES if focus_node_id in {edge.source_node_id, edge.target_node_id}]
    node_ids = {focus_node_id} | {edge.source_node_id for edge in edges} | {edge.target_node_id for edge in edges}
    nodes = [node for node in GRAPH_NODES if node.id in node_ids]
    return GraphView(view="neighborhood", nodes=nodes, edges=edges)
