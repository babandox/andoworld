from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import asdict
from typing import Any

from neo4j import GraphDatabase

from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.structural_demographic import MacroState


class Neo4jGraph:
    """Neo4j-backed implementation of the InMemoryGraph contract."""

    def __init__(self, driver: Any, *, database: str | None = None) -> None:
        self._driver = driver
        self._database = database

    @classmethod
    def from_uri(cls, uri: str, auth: tuple[str, str], *, database: str | None = None) -> "Neo4jGraph":
        return cls(GraphDatabase.driver(uri, auth=auth), database=database)

    def close(self) -> None:
        self._driver.close()

    def add_node(self, node_id: Hashable, **properties: Any) -> None:
        self._execute_write(
            """
            MERGE (n:GraphNode {id: $node_id})
            SET n += $properties
            """,
            node_id=node_id,
            properties=dict(properties),
        )

    def set_node_property(self, node_id: Hashable, name: str, value: Any) -> None:
        record = self._single_record(
            self._execute_write(
                """
                MATCH (n:GraphNode {id: $node_id})
                SET n += $properties
                RETURN count(n) AS updated
                """,
                node_id=node_id,
                properties={name: value},
            )
        )
        if record["updated"] == 0:
            raise ValueError(f"Graph node does not exist: {node_id!r}")

    def node_properties(self, node_id: Hashable) -> dict[str, Any]:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (n:GraphNode {id: $node_id})
                RETURN properties(n) AS properties
                """,
                node_id=node_id,
            ),
            missing_message=f"Graph node does not exist: {node_id!r}",
        )
        return self._public_properties(record["properties"])

    def add_edge(self, source: Hashable, target: Hashable, **properties: Any) -> None:
        self._execute_write(
            """
            MERGE (source:GraphNode {id: $source})
            MERGE (target:GraphNode {id: $target})
            MERGE (source)-[r:CONNECTED_TO]->(target)
            SET r += $properties
            """,
            source=source,
            target=target,
            properties=dict(properties),
        )

    def neighbors(self, node_id: Hashable) -> list[Hashable]:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (n:GraphNode {id: $node_id})
                OPTIONAL MATCH (n)-[:CONNECTED_TO]->(neighbor:GraphNode)
                WITH n, neighbor
                ORDER BY neighbor.id
                RETURN n.id AS node_id, [id IN collect(neighbor.id) WHERE id IS NOT NULL] AS ids
                """,
                node_id=node_id,
            ),
            missing_message=f"Graph node does not exist: {node_id!r}",
        )
        return list(record["ids"])

    def predecessors(self, node_id: Hashable) -> list[Hashable]:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (n:GraphNode {id: $node_id})
                OPTIONAL MATCH (predecessor:GraphNode)-[:CONNECTED_TO]->(n)
                WITH n, predecessor
                ORDER BY predecessor.id
                RETURN n.id AS node_id, [id IN collect(predecessor.id) WHERE id IS NOT NULL] AS ids
                """,
                node_id=node_id,
            ),
            missing_message=f"Graph node does not exist: {node_id!r}",
        )
        return list(record["ids"])

    def edge_property(self, source: Hashable, target: Hashable, name: str, default: Any = None) -> Any:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (:GraphNode {id: $source})-[r:CONNECTED_TO]->(:GraphNode {id: $target})
                RETURN r[$name] AS value
                """,
                source=source,
                target=target,
                name=name,
            ),
            missing_message=f"Graph edge does not exist: {source!r} -> {target!r}",
        )
        return default if record["value"] is None else record["value"]

    def degree(self, node_id: Hashable) -> int:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (n:GraphNode {id: $node_id})
                OPTIONAL MATCH (n)-[r:CONNECTED_TO]->()
                RETURN n.id AS node_id, count(r) AS degree
                """,
                node_id=node_id,
            ),
            missing_message=f"Graph node does not exist: {node_id!r}",
        )
        return int(record["degree"])

    def edges_between(self, community_a: Iterable[Hashable], community_b: Iterable[Hashable]) -> int:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (source:GraphNode)-[r:CONNECTED_TO]->(target:GraphNode)
                WHERE (source.id IN $community_a AND target.id IN $community_b)
                   OR (source.id IN $community_b AND target.id IN $community_a)
                RETURN count(r) AS width
                """,
                community_a=list(community_a),
                community_b=list(community_b),
            )
        )
        return int(record["width"])

    def save_macro_state(self, state_id: Hashable, state: MacroState) -> None:
        self._execute_write(
            """
            MERGE (s:GraphNode:State {id: $state_id})
            SET s += $properties
            """,
            state_id=state_id,
            properties=asdict(state),
        )

    def load_macro_state(self, state_id: Hashable) -> MacroState:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (s:GraphNode:State {id: $state_id})
                RETURN properties(s) AS properties
                """,
                state_id=state_id,
            ),
            missing_message=f"Macro state does not exist: {state_id!r}",
        )
        properties = self._public_properties(record["properties"])
        return MacroState(**properties)

    def save_agent_zero(self, agent: AgentZero) -> None:
        properties = asdict(agent)
        agent_id = properties.pop("unique_id")
        self._execute_write(
            """
            MERGE (a:GraphNode:AgentZero {id: $agent_id})
            SET a += $properties
            """,
            agent_id=agent_id,
            properties=properties,
        )

    def load_agent_zero(self, agent_id: Hashable) -> AgentZero:
        record = self._single_record(
            self._execute_read(
                """
                MATCH (a:GraphNode:AgentZero {id: $agent_id})
                RETURN properties(a) AS properties
                """,
                agent_id=agent_id,
            ),
            missing_message=f"AgentZero node does not exist: {agent_id!r}",
        )
        properties = self._public_properties(record["properties"])
        return AgentZero(unique_id=agent_id, **properties)

    def _execute_read(self, query: str, **parameters: Any) -> list[Any]:
        with self._driver.session(database=self._database) as session:
            return session.execute_read(self._collect_records, query, parameters)

    def _execute_write(self, query: str, **parameters: Any) -> list[Any]:
        with self._driver.session(database=self._database) as session:
            return session.execute_write(self._collect_records, query, parameters)

    @staticmethod
    def _collect_records(transaction: Any, query: str, parameters: dict[str, Any]) -> list[Any]:
        return list(transaction.run(query, **parameters))

    @staticmethod
    def _single_record(records: list[Any], *, missing_message: str = "Neo4j query returned no records") -> Any:
        if not records:
            raise ValueError(missing_message)
        return records[0]

    @staticmethod
    def _public_properties(properties: dict[str, Any]) -> dict[str, Any]:
        public = dict(properties)
        public.pop("id", None)
        return public
