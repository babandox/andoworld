from backend.app.iran_war.entity_resolution import EntityResolver


def test_irgc_aliases_resolve_to_same_canonical_entity():
    resolver = EntityResolver.with_default_seed()

    irgc = resolver.resolve("IRGC")
    full = resolver.resolve("Islamic Revolutionary Guard Corps")
    guards = resolver.resolve("Revolutionary Guards")

    assert irgc is not None
    assert full is not None
    assert guards is not None
    assert {irgc.entity_id, full.entity_id, guards.entity_id} == {"entity:irgc"}


def test_ambiguous_tehran_can_remain_unresolved():
    resolver = EntityResolver.with_default_seed()

    mention = resolver.resolve("Tehran")

    assert mention is not None
    assert mention.entity_id is None
    assert mention.status == "ambiguous"
