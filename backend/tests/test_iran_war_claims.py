from backend.app.iran_war.claims import (
    AtomicClaim,
    ClaimClusterer,
    ContradictionDetector,
    SemanticBlocker,
)


def test_semantic_blocking_uses_canonical_entities_before_nli():
    claims = [
        AtomicClaim(
            id="claim:1",
            subject="IRGC",
            predicate="threatened",
            object="retaliation",
            occurred_at="2026-02-20",
            quote="The IRGC threatened retaliation.",
            source_ids=["source:a"],
            canonical_entity_ids=["entity:irgc"],
        ),
        AtomicClaim(
            id="claim:2",
            subject="Islamic Revolutionary Guard Corps",
            predicate="denied",
            object="retaliation plan",
            occurred_at="2026-02-20",
            quote="The Islamic Revolutionary Guard Corps denied a retaliation plan.",
            source_ids=["source:b"],
            canonical_entity_ids=["entity:irgc"],
        ),
        AtomicClaim(
            id="claim:3",
            subject="S&P 500",
            predicate="closed",
            object="lower",
            occurred_at="2026-02-20",
            quote="The S&P 500 closed lower.",
            source_ids=["source:c"],
            canonical_entity_ids=["entity:sp500"],
        ),
    ]

    pairs = SemanticBlocker().candidate_pairs(claims)

    assert ("claim:1", "claim:2") in pairs
    assert ("claim:1", "claim:3") not in pairs


def test_contradiction_detector_marks_same_day_opposing_claims_as_disputed():
    claims = [
        AtomicClaim(
            id="claim:1",
            subject="Trump",
            predicate="supported",
            object="ceasefire",
            occurred_at="2026-03-03",
            quote="Trump supported a ceasefire.",
            source_ids=["source:a"],
            canonical_entity_ids=["entity:trump"],
        ),
        AtomicClaim(
            id="claim:2",
            subject="Trump",
            predicate="rejected",
            object="ceasefire",
            occurred_at="2026-03-03",
            quote="Trump rejected a ceasefire.",
            source_ids=["source:b"],
            canonical_entity_ids=["entity:trump"],
        ),
    ]

    clusters = ClaimClusterer().cluster(claims)
    contradictions = ContradictionDetector().detect(claims)

    assert clusters[0].status == "disputed"
    assert contradictions[0].relationship == "contradicts"
    assert contradictions[0].source_claim_id == "claim:1"
    assert contradictions[0].target_claim_id == "claim:2"


def test_contradiction_detector_marks_cross_day_actor_flip_as_reversal():
    claims = [
        AtomicClaim(
            id="claim:1",
            subject="Trump",
            predicate="supported",
            object="ceasefire",
            occurred_at="2026-03-03",
            quote="Trump supported a ceasefire.",
            source_ids=["source:a"],
            canonical_entity_ids=["entity:trump"],
        ),
        AtomicClaim(
            id="claim:2",
            subject="Trump",
            predicate="rejected",
            object="ceasefire",
            occurred_at="2026-03-04",
            quote="Trump rejected a ceasefire.",
            source_ids=["source:b"],
            canonical_entity_ids=["entity:trump"],
        ),
    ]

    contradictions = ContradictionDetector().detect(claims)

    assert contradictions[0].relationship == "reversal"
