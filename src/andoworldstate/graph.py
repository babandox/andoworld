from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import Any


class InMemoryGraph:
    """Directed property graph boundary shaped for later Neo4j replacement."""

    def __init__(self) -> None:
        self._nodes: dict[Hashable, dict[str, Any]] = {}
        self._edges: dict[Hashable, dict[Hashable, dict[str, Any]]] = {}

    def add_node(self, node_id: Hashable, **properties: Any) -> None:
        existing = self._nodes.setdefault(node_id, {})
        existing.update(properties)
        self._edges.setdefault(node_id, {})

    def set_node_property(self, node_id: Hashable, name: str, value: Any) -> None:
        self._require_node(node_id)
        self._nodes[node_id][name] = value

    def node_properties(self, node_id: Hashable) -> dict[str, Any]:
        self._require_node(node_id)
        return dict(self._nodes[node_id])

    def add_edge(self, source: Hashable, target: Hashable, **properties: Any) -> None:
        self.add_node(source)
        self.add_node(target)
        self._edges[source][target] = dict(properties)

    def neighbors(self, node_id: Hashable) -> list[Hashable]:
        self._require_node(node_id)
        return list(self._edges[node_id])

    def predecessors(self, node_id: Hashable) -> list[Hashable]:
        self._require_node(node_id)
        return [source for source, targets in self._edges.items() if node_id in targets]

    def edge_property(self, source: Hashable, target: Hashable, name: str, default: Any = None) -> Any:
        self._require_edge(source, target)
        return self._edges[source][target].get(name, default)

    def degree(self, node_id: Hashable) -> int:
        self._require_node(node_id)
        return len(self._edges[node_id])

    def edges_between(self, community_a: Iterable[Hashable], community_b: Iterable[Hashable]) -> int:
        a_nodes = set(community_a)
        b_nodes = set(community_b)
        width = 0
        for source, targets in self._edges.items():
            for target in targets:
                if (source in a_nodes and target in b_nodes) or (source in b_nodes and target in a_nodes):
                    width += 1
        return width

    def _require_node(self, node_id: Hashable) -> None:
        if node_id not in self._nodes:
            raise ValueError(f"Graph node does not exist: {node_id!r}")

    def _require_edge(self, source: Hashable, target: Hashable) -> None:
        self._require_node(source)
        self._require_node(target)
        if target not in self._edges[source]:
            raise ValueError(f"Graph edge does not exist: {source!r} -> {target!r}")

