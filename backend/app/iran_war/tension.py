from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re

from backend.app.models import TensionSeriesPoint, TimelineEvent


BASELINE = 40.0
DAILY_REVERSION_RATE = 0.08
MAX_DAILY_INCREASE = 16.0
MAX_DAILY_DECREASE = -18.0
TENSION_CEILING = 92.0
TENSION_FLOOR = 8.0
TENSION_EVENT_CATEGORIES = {"prelude", "statement", "strike", "diplomacy", "impact", "current_state"}


@dataclass(frozen=True)
class TensionClassification:
    delta: float
    label: str


def classify_tension_event(event: TimelineEvent) -> TensionClassification:
    text = f"{event.title} {event.summary}".casefold()
    delta = 0.0
    labels: list[str] = []

    deescalation = _matches(
        text,
        r"\b(ceasefire|truce|peace deal|peace talks|talks resume|diplomacy|proposal|mediat(?:e|ion|or)|unrestricted shipping|blockade.*lifted|restraint|de-escalat(?:e|ion)|end the war)\b",
    )
    major_escalation = _matches(
        text,
        r"\b(missile attack|drone attack|air strike|airstrike|strike hit|struck|attack|attacked|missile|missiles|targeted|targets|killed|air defense|cluster munition|nuclear facility|ballistic)\b",
    ) and not _matches(text, r"\b(no new|without new|end|ending|ended)\s+(strike|strikes|attack|attacks)\b")
    moderate_escalation = _matches(
        text,
        r"\b(blockade|close(?:d|s)? the strait|airspace|warship|sanction|sanctions|threat|threaten|warns|warning|shipping disrupted|shipping risk|attack(?:s)? on shipping)\b",
    )
    rhetorical_escalation = _matches(text, r"\b(trump|truth social|regime change|ultimatum|rhetoric|statement)\b")
    uncertainty = _matches(text, r"\b(disputed|unclear|unconfirmed|contradict|conflicting)\b")

    if deescalation:
        delta -= 12.0
        labels.append("de-escalation")
    if major_escalation:
        delta += 12.0
        labels.append("major escalation")
    if moderate_escalation:
        delta += 6.0
        labels.append("moderate escalation")
    if rhetorical_escalation and not deescalation:
        delta += 2.0
        labels.append("rhetorical escalation")
    if uncertainty:
        delta += 1.0
        labels.append("uncertainty")

    if not labels:
        return TensionClassification(delta=0.0, label="no tension signal")
    return TensionClassification(delta=delta, label=", ".join(labels))


def build_tension_series(events: list[TimelineEvent], start: str, end: str) -> list[TensionSeriesPoint]:
    start_date = _date(start)
    end_date = _date(end)
    events_by_date: dict[str, list[TimelineEvent]] = {}
    for event in events:
        if event.category not in TENSION_EVENT_CATEGORIES:
            continue
        day = event.occurred_at[:10]
        if start <= day <= end:
            events_by_date.setdefault(day, []).append(event)

    value = BASELINE
    points: list[TensionSeriesPoint] = []
    cursor = start_date
    while cursor <= end_date:
        day = cursor.isoformat()
        day_events = events_by_date.get(day, [])
        value += (BASELINE - value) * DAILY_REVERSION_RATE

        scored_events = [(event, classify_tension_event(event)) for event in day_events]
        delta = _daily_delta([classification for _, classification in scored_events])
        value = _apply_daily_delta(value, delta)
        contributing = [event for event, classification in scored_events if classification.delta != 0]
        points.append(
            TensionSeriesPoint(
                date=day,
                value=round(value, 2),
                source="rule_based",
                source_ids=_source_ids(contributing),
                summary=_summary(contributing, delta),
            )
        )
        cursor += timedelta(days=1)
    return points


def _matches(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, re.IGNORECASE))


def _date(value: str) -> date:
    return datetime.fromisoformat(value[:10]).date()


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _daily_delta(classifications: list[TensionClassification]) -> float:
    positives = sorted((classification.delta for classification in classifications if classification.delta > 0), reverse=True)
    negatives = sorted(classification.delta for classification in classifications if classification.delta < 0)
    positive_delta = sum(positives[:4])
    negative_delta = sum(negatives[:4])
    return max(MAX_DAILY_DECREASE, min(MAX_DAILY_INCREASE, positive_delta + negative_delta))


def _apply_daily_delta(value: float, delta: float) -> float:
    if delta > 0:
        headroom = max(0.0, TENSION_CEILING - value)
        return _clamp(value + min(delta, headroom * 0.45))
    if delta < 0:
        room_to_floor = max(0.0, value - TENSION_FLOOR)
        return _clamp(value + max(delta, -room_to_floor * 0.55))
    return _clamp(value)


def _source_ids(events: list[TimelineEvent]) -> list[str]:
    source_ids: list[str] = []
    for event in events:
        for source_id in event.source_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
    return source_ids


def _summary(events: list[TimelineEvent], delta: float) -> str:
    if not events:
        return "No dated escalation signal; tension decays toward baseline."
    direction = "raised" if delta > 0 else "lowered" if delta < 0 else "held"
    titles = "; ".join(event.title for event in events[:3])
    return f"{len(events)} dated source event(s) {direction} the tension index: {titles}"
