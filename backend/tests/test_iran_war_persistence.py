from backend.app.iran_war.persistence import _upsert_payloads


class FakeConnection:
    def __init__(self):
        self.statements: list[str] = []

    def execute(self, sql: str, params=None):
        self.statements.append(" ".join(sql.split()))


def test_upsert_payloads_can_preserve_existing_cache_rows_without_pruning():
    conn = FakeConnection()

    _upsert_payloads(conn, "iran_war_source_documents", [("gdelt:1", "gdelt", {"id": "gdelt:1"})], prune_missing=False)

    assert not any(statement.startswith("delete from iran_war_source_documents") for statement in conn.statements)
