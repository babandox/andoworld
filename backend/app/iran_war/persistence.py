from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import hashlib
import json
import re
import uuid

from backend.app.iran_war.config import database_url, qdrant_url
from backend.app.models import IranWarCase, SourceDocument


QDRANT_COLLECTION = "iran_war_sources"
VECTOR_SIZE = 64


@dataclass
class PersistenceResult:
    postgres_available: bool
    qdrant_available: bool
    postgres_note: str
    qdrant_note: str


def persist_case_artifacts(case: IranWarCase) -> PersistenceResult:
    postgres_available, postgres_note = _persist_postgres(case)
    qdrant_available, qdrant_note = _persist_qdrant(case.source_documents)
    return PersistenceResult(
        postgres_available=postgres_available,
        qdrant_available=qdrant_available,
        postgres_note=postgres_note,
        qdrant_note=qdrant_note,
    )


def persist_source_documents(source_documents: list[SourceDocument]) -> PersistenceResult:
    postgres_available, postgres_note = _persist_source_documents_postgres(source_documents)
    return PersistenceResult(
        postgres_available=postgres_available,
        qdrant_available=False,
        postgres_note=postgres_note,
        qdrant_note="Qdrant indexing skipped for source-document-only backfill.",
    )


def load_cached_source_documents(source_type: str, limit: int = 100) -> list[SourceDocument]:
    try:
        import psycopg
    except ImportError:
        return []

    try:
        with psycopg.connect(database_url(), connect_timeout=2) as conn:
            _ensure_postgres_tables(conn)
            rows = conn.execute(
                """
                select payload
                from iran_war_source_documents
                where record_type = %s
                order by coalesce(payload->>'published_at', payload->>'retrieved_at', '') desc
                limit %s
                """,
                (source_type, limit),
            ).fetchall()
    except Exception:
        return []

    docs: list[SourceDocument] = []
    for (payload,) in rows:
        try:
            docs.append(SourceDocument(**payload))
        except Exception:
            continue
    return docs


def _persist_postgres(case: IranWarCase) -> tuple[bool, str]:
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError:
        return False, "Postgres driver psycopg is not installed; canonical records were not persisted."

    try:
        with psycopg.connect(database_url(), connect_timeout=2) as conn:
            _ensure_postgres_tables(conn)
            run_id = f"run:{datetime.now(timezone.utc).isoformat()}"
            conn.execute(
                """
                insert into iran_war_ingestion_runs (id, payload)
                values (%s, %s)
                on conflict (id) do update set payload = excluded.payload, updated_at = now()
                """,
                (
                    run_id,
                    Jsonb(
                        {
                            "source_documents": len(case.source_documents),
                            "graph_nodes": len(case.graph_view.nodes),
                            "graph_edges": len(case.graph_view.edges),
                            "claim_clusters": len(case.claim_clusters),
                            "market_series_points": len(case.market_series),
                            "prediction_market_series_points": len(case.prediction_market_series),
                            "extraction_method": case.extraction_status.method,
                        }
                    ),
                ),
            )
            _upsert_payloads(
                conn,
                "iran_war_source_documents",
                [(source.id, source.source_type, source.model_dump(mode="json")) for source in case.source_documents],
                prune_missing=False,
            )
            _upsert_payloads(conn, "iran_war_graph_nodes", [(node.id, node.node_type, node.model_dump(mode="json")) for node in case.graph_view.nodes])
            _upsert_payloads(conn, "iran_war_graph_edges", [(edge.id, edge.relation, edge.model_dump(mode="json")) for edge in case.graph_view.edges])
            _upsert_payloads(conn, "iran_war_claim_clusters", [(cluster.id, cluster.status, cluster.model_dump(mode="json")) for cluster in case.claim_clusters])
            _upsert_payloads(
                conn,
                "iran_war_market_series_points",
                [
                    (f"{point.series}:{point.date}", point.series, point.model_dump(mode="json"))
                    for point in case.market_series
                ],
            )
            _upsert_payloads(
                conn,
                "iran_war_prediction_market_price_points",
                [
                    (f"{point.market_id}:{point.token_id}:{point.date}", "polymarket", point.model_dump(mode="json"))
                    for point in case.prediction_market_series
                ],
            )
        return True, f"Persisted canonical case records to Postgres: {len(case.source_documents)} sources, {len(case.graph_view.nodes)} nodes, {len(case.graph_view.edges)} edges, {len(case.prediction_market_series)} Polymarket price points."
    except Exception as exc:
        return False, f"Postgres persistence unavailable: {type(exc).__name__}."


def _persist_source_documents_postgres(source_documents: list[SourceDocument]) -> tuple[bool, str]:
    try:
        import psycopg
    except ImportError:
        return False, "Postgres driver psycopg is not installed; source documents were not persisted."

    try:
        with psycopg.connect(database_url(), connect_timeout=2) as conn:
            _ensure_postgres_tables(conn)
            _upsert_payloads(
                conn,
                "iran_war_source_documents",
                [(source.id, source.source_type, source.model_dump(mode="json")) for source in source_documents],
                prune_missing=False,
            )
        return True, f"Persisted {len(source_documents)} source documents to Postgres."
    except Exception as exc:
        return False, f"Postgres source-document persistence unavailable: {type(exc).__name__}."


def _ensure_postgres_tables(conn: Any) -> None:
    tables = {
        "iran_war_source_documents": "record_type text not null",
        "iran_war_graph_nodes": "record_type text not null",
        "iran_war_graph_edges": "record_type text not null",
        "iran_war_claim_clusters": "record_type text not null",
        "iran_war_market_series_points": "record_type text not null",
        "iran_war_prediction_market_price_points": "record_type text not null",
        "iran_war_ingestion_runs": "",
    }
    for table, extra_columns in tables.items():
        record_type_column = f", {extra_columns}" if extra_columns else ""
        conn.execute(
            f"""
            create table if not exists {table} (
                id text primary key
                {record_type_column},
                payload jsonb not null,
                updated_at timestamptz not null default now()
            )
            """
        )


def _upsert_payloads(conn: Any, table: str, rows: list[tuple[str, str, dict[str, Any]]], prune_missing: bool = True) -> None:
    from psycopg.types.json import Jsonb

    if not rows:
        if prune_missing:
            conn.execute(f"delete from {table}")
        return

    for record_id, record_type, payload in rows:
        conn.execute(
            f"""
            insert into {table} (id, record_type, payload)
            values (%s, %s, %s)
            on conflict (id) do update
            set record_type = excluded.record_type, payload = excluded.payload, updated_at = now()
            """,
            (record_id, record_type, Jsonb(payload)),
        )
    if prune_missing:
        conn.execute(f"delete from {table} where not (id = any(%s))", ([record_id for record_id, _, _ in rows],))


def _persist_qdrant(source_documents: list[SourceDocument]) -> tuple[bool, str]:
    if not source_documents:
        return False, "Qdrant index skipped because no source documents were available."

    try:
        _ensure_qdrant_collection(recreate=True)
        points = [
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, source.id)),
                "vector": _hash_vector(f"{source.title} {source.section_title or ''} {source.excerpt}"),
                "payload": {
                    "source_document_id": source.id,
                    "source_type": source.source_type,
                    "title": source.title,
                    "published_at": source.published_at,
                    "retrieved_at": source.retrieved_at,
                    "section_title": source.section_title,
                    "url": source.url,
                },
            }
            for source in source_documents
        ]
        _qdrant_json(
            f"/collections/{QDRANT_COLLECTION}/points?wait=true",
            method="PUT",
            payload={"points": points},
        )
        return True, f"Indexed {len(points)} source documents in Qdrant collection {QDRANT_COLLECTION}."
    except Exception as exc:
        return False, f"Qdrant indexing unavailable: {type(exc).__name__}."


def _ensure_qdrant_collection(recreate: bool = False) -> None:
    if recreate:
        try:
            _qdrant_json(f"/collections/{QDRANT_COLLECTION}", method="DELETE")
        except HTTPError as exc:
            if exc.code != 404:
                raise

    try:
        _qdrant_json(f"/collections/{QDRANT_COLLECTION}")
        return
    except HTTPError as exc:
        if exc.code != 404:
            raise

    _qdrant_json(
        f"/collections/{QDRANT_COLLECTION}",
        method="PUT",
        payload={"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}},
    )


def _qdrant_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    base_url = qdrant_url().rstrip("/")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(request, timeout=5) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _hash_vector(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    for token in re.findall(r"[a-z0-9]+", text.casefold()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]
