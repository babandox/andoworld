from backend.app.iran_war.causal_extraction import DEFAULT_OPENAI_EXTRACTION_MODEL, _build_openai_chat_payload, _coerce_openai_graph
from backend.app.models import SourceDocument


def test_openai_graph_coercion_accepts_numeric_confidence_and_historical_claim_type():
    source = SourceDocument(
        id="wiki:test:background",
        source_type="wikipedia",
        title="2026 Iran war - Background",
        retrieved_at="2026-05-10",
        section_title="Background",
        excerpt="The background included the Iran nuclear program.",
    )
    payload = {
        "nodes": [
            {
                "id": "node1",
                "label": "Iran nuclear issue",
                "node_type": "strategic_driver",
                "summary": "The nuclear issue shaped the war rationale.",
                "source_ids": [source.id],
                "confidence": 0.9,
                "claim_type": "historical",
            },
            {
                "id": "node2",
                "label": "Stated rationale",
                "node_type": "actor_rationale",
                "summary": "Actors cited nuclear risk.",
                "source_ids": [source.id],
                "confidence": "medium",
                "claim_type": "actor_stated_rationale",
            },
            {
                "id": "node3",
                "label": "War start",
                "node_type": "opening_event",
                "summary": "The rationale connected to the opening event.",
                "source_ids": [source.id],
                "confidence": "high",
                "claim_type": "reported_fact",
            },
        ],
        "edges": [
            {
                "id": "edge1",
                "source_node_id": "node1",
                "target_node_id": "node2",
                "relation": "justifies",
                "summary": "The nuclear issue was cited in stated rationales.",
                "source_ids": [source.id],
                "confidence": 0.8,
                "claim_type": "historical",
            }
        ],
    }

    extraction = _coerce_openai_graph(payload, [source])

    assert extraction is not None
    assert extraction.method == "openai"
    assert len(extraction.graph_view.nodes) == 3
    assert extraction.graph_view.nodes[0].confidence == "high"
    assert extraction.graph_view.nodes[0].claim_type == "actor_stated_rationale"
    assert extraction.graph_view.edges[0].confidence == "high"


def test_default_openai_extraction_model_is_gpt_55():
    assert DEFAULT_OPENAI_EXTRACTION_MODEL == "gpt-5.5"


def test_gpt_55_payload_omits_unsupported_temperature():
    payload = _build_openai_chat_payload(model="gpt-5.5", prompt="Return JSON.")

    assert payload["model"] == "gpt-5.5"
    assert "temperature" not in payload
    assert payload["response_format"] == {"type": "json_object"}
