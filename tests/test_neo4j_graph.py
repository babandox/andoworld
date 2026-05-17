from math import isclose

from andoworldstate.graph import InMemoryGraph
from andoworldstate.neo4j_graph import Neo4jGraph
from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.structural_demographic import MacroState


class FakeResult:
    def __init__(self, records):
        self.records = records

    def __iter__(self):
        return iter(self.records)

    def consume(self):
        return None


class FakeTransaction:
    def __init__(self, driver):
        self.driver = driver

    def run(self, query, **parameters):
        self.driver.queries.append((squash(query), parameters))
        records = self.driver.results.pop(0) if self.driver.results else []
        return FakeResult(records)


class FakeSession:
    def __init__(self, driver, database):
        self.driver = driver
        self.database = database

    def __enter__(self):
        self.driver.databases.append(self.database)
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute_read(self, callback, *args):
        return callback(FakeTransaction(self.driver), *args)

    def execute_write(self, callback, *args):
        return callback(FakeTransaction(self.driver), *args)


class FakeDriver:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.queries = []
        self.databases = []
        self.closed = False

    def session(self, *, database=None):
        return FakeSession(self, database)

    def close(self):
        self.closed = True


def squash(query):
    return " ".join(query.split())


def test_neo4j_add_node_maps_to_graph_node_merge_with_property_map():
    driver = FakeDriver()
    graph = Neo4jGraph(driver, database="sim")

    graph.add_node("agent-1", affect_v=0.2, cognition_p=0.3)

    query, parameters = driver.queries[-1]
    assert "MERGE (n:GraphNode {id: $node_id})" in query
    assert "SET n += $properties" in query
    assert parameters == {"node_id": "agent-1", "properties": {"affect_v": 0.2, "cognition_p": 0.3}}
    assert driver.databases == ["sim"]


def test_neo4j_graph_contract_matches_in_memory_neighbor_and_edge_property_operations():
    memory_graph = InMemoryGraph()
    memory_graph.add_edge("a", "b", omega=0.7)
    driver = FakeDriver(results=[[{"ids": ["b"]}], [{"value": 0.7}]])
    neo4j_graph = Neo4jGraph(driver)

    assert neo4j_graph.neighbors("a") == memory_graph.neighbors("a")
    assert neo4j_graph.edge_property("a", "b", "omega") == memory_graph.edge_property("a", "b", "omega")

    neighbor_query, neighbor_parameters = driver.queries[0]
    edge_query, edge_parameters = driver.queries[1]
    assert "MATCH (n:GraphNode {id: $node_id})" in neighbor_query
    assert "OPTIONAL MATCH (n)-[:CONNECTED_TO]->(neighbor:GraphNode)" in neighbor_query
    assert "WITH n, neighbor" in neighbor_query
    assert "RETURN n.id AS node_id" in neighbor_query
    assert neighbor_parameters == {"node_id": "a"}
    assert "MATCH (:GraphNode {id: $source})-[r:CONNECTED_TO]->(:GraphNode {id: $target})" in edge_query
    assert "RETURN r[$name] AS value" in edge_query
    assert edge_parameters == {"source": "a", "target": "b", "name": "omega"}


def test_neo4j_add_edge_maps_to_connected_to_relationship_merge():
    driver = FakeDriver()
    graph = Neo4jGraph(driver)

    graph.add_edge("a", "b", omega=0.4)

    query, parameters = driver.queries[-1]
    assert "MERGE (source:GraphNode {id: $source})" in query
    assert "MERGE (target:GraphNode {id: $target})" in query
    assert "MERGE (source)-[r:CONNECTED_TO]->(target)" in query
    assert "SET r += $properties" in query
    assert parameters == {"source": "a", "target": "b", "properties": {"omega": 0.4}}


def test_neo4j_node_properties_excludes_storage_id_property_to_match_in_memory_contract():
    driver = FakeDriver(results=[[{"properties": {"id": "a", "affect_v": 0.2}}]])
    graph = Neo4jGraph(driver)

    assert graph.node_properties("a") == {"affect_v": 0.2}


def test_neo4j_save_and_load_macro_state_uses_state_label_and_turchin_properties():
    state = MacroState(
        relative_wage=0.5,
        urbanization_ratio=0.8,
        youth_bulge=0.25,
        relative_elite_income=0.4,
        elite_ratio=0.1,
        debt_to_gdp=0.6,
        distrust=0.5,
    )
    driver = FakeDriver(
        results=[
            [],
            [
                {
                    "properties": {
                        "id": "Country_X",
                        "relative_wage": 0.5,
                        "urbanization_ratio": 0.8,
                        "youth_bulge": 0.25,
                        "relative_elite_income": 0.4,
                        "elite_ratio": 0.1,
                        "debt_to_gdp": 0.6,
                        "distrust": 0.5,
                    }
                }
            ],
        ]
    )
    graph = Neo4jGraph(driver)

    graph.save_macro_state("Country_X", state)
    loaded = graph.load_macro_state("Country_X")

    save_query, save_parameters = driver.queries[0]
    assert "MERGE (s:GraphNode:State {id: $state_id})" in save_query
    assert save_parameters["state_id"] == "Country_X"
    assert save_parameters["properties"]["relative_wage"] == 0.5
    assert loaded == state


def test_neo4j_save_and_load_agent_zero_uses_agent_label_and_epstein_properties():
    agent = AgentZero(
        unique_id="agent-1",
        learning_rate_alpha=0.5,
        salience_beta=0.25,
        activation_threshold_tau=1.0,
        affect_v=0.2,
        cognition_p=0.3,
        action=1,
    )
    driver = FakeDriver(
        results=[
            [],
            [
                {
                    "properties": {
                        "id": "agent-1",
                        "learning_rate_alpha": 0.5,
                        "salience_beta": 0.25,
                        "activation_threshold_tau": 1.0,
                        "affect_v": 0.2,
                        "cognition_p": 0.3,
                        "action": 1,
                    }
                }
            ],
        ]
    )
    graph = Neo4jGraph(driver)

    graph.save_agent_zero(agent)
    loaded = graph.load_agent_zero("agent-1")

    save_query, save_parameters = driver.queries[0]
    assert "MERGE (a:GraphNode:AgentZero {id: $agent_id})" in save_query
    assert save_parameters["agent_id"] == "agent-1"
    assert save_parameters["properties"]["activation_threshold_tau"] == 1.0
    assert loaded == agent


def test_agent_zero_step_can_swap_in_neo4j_graph_dependency_for_social_contagion():
    driver = FakeDriver(results=[[{"ids": ["b"]}], [{"value": 1.0}]])
    graph = Neo4jGraph(driver)
    agents = {
        "a": AgentZero("a", 1.0, 1.0, 0.75),
        "b": AgentZero("b", 0.1, 0.1, 1.0, affect_v=0.1, cognition_p=0.1),
    }

    agents["a"].step(graph, agents, environmental_threat_lambda=0.4, local_risk=0.2)

    assert agents["a"].action == 1
    assert isclose(agents["a"].affect_v, 0.4)
