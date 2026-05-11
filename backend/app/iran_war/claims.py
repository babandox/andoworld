from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


OPPOSING_PREDICATES = {
    ("supported", "rejected"),
    ("rejected", "supported"),
    ("threatened", "denied"),
    ("denied", "threatened"),
    ("confirmed", "denied"),
    ("denied", "confirmed"),
}


@dataclass(frozen=True)
class AtomicClaim:
    id: str
    subject: str
    predicate: str
    object: str
    occurred_at: str
    quote: str
    source_ids: list[str]
    canonical_entity_ids: list[str]
    claim_type: str = "reported_fact"


@dataclass(frozen=True)
class ClaimCluster:
    id: str
    claim_ids: list[str]
    status: str
    summary: str
    canonical_entity_ids: list[str]


@dataclass(frozen=True)
class ClaimContradiction:
    id: str
    source_claim_id: str
    target_claim_id: str
    relationship: str
    confidence: str
    rationale: str


class SemanticBlocker:
    def candidate_pairs(self, claims: list[AtomicClaim]) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for left, right in combinations(claims, 2):
            shared_entities = set(left.canonical_entity_ids) & set(right.canonical_entity_ids)
            same_day = left.occurred_at == right.occurred_at
            same_object = left.object.casefold() == right.object.casefold()
            if shared_entities and (same_day or same_object):
                pairs.add((left.id, right.id))
        return pairs


class ContradictionDetector:
    def detect(self, claims: list[AtomicClaim]) -> list[ClaimContradiction]:
        results: list[ClaimContradiction] = []
        claim_by_id = {claim.id: claim for claim in claims}
        for left_id, right_id in SemanticBlocker().candidate_pairs(claims):
            left = claim_by_id[left_id]
            right = claim_by_id[right_id]
            relationship = self._relationship(left, right)
            if relationship in {"contradicts", "reversal"}:
                results.append(
                    ClaimContradiction(
                        id=f"contradiction:{left.id}:{right.id}",
                        source_claim_id=left.id,
                        target_claim_id=right.id,
                        relationship=relationship,
                        confidence="medium",
                        rationale="Opposing predicates share canonical entities and proposition object.",
                    )
                )
        return results

    def _relationship(self, left: AtomicClaim, right: AtomicClaim) -> str:
        predicates = (left.predicate.casefold(), right.predicate.casefold())
        if predicates not in OPPOSING_PREDICATES:
            return "unrelated"
        if left.occurred_at == right.occurred_at:
            return "contradicts"
        return "reversal"


class ClaimClusterer:
    def cluster(self, claims: list[AtomicClaim]) -> list[ClaimCluster]:
        contradictions = ContradictionDetector().detect(claims)
        disputed_ids = {
            claim_id
            for contradiction in contradictions
            if contradiction.relationship == "contradicts"
            for claim_id in (contradiction.source_claim_id, contradiction.target_claim_id)
        }
        if not claims:
            return []

        canonical_entities = sorted({entity for claim in claims for entity in claim.canonical_entity_ids})
        status = "disputed" if disputed_ids else "accepted"
        return [
            ClaimCluster(
                id="cluster:case-core",
                claim_ids=[claim.id for claim in claims],
                status=status,
                summary="Core Iran-war claim cluster derived from source-backed claims.",
                canonical_entity_ids=canonical_entities,
            )
        ]
