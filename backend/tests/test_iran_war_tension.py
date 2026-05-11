from backend.app.iran_war.tension import build_tension_series, classify_tension_event
from backend.app.models import TimelineEvent


def event(
    event_id: str,
    date: str,
    title: str,
    summary: str,
    source_id: str,
    category: str = "prelude",
) -> TimelineEvent:
    return TimelineEvent(
        id=event_id,
        occurred_at=date,
        title=title,
        summary=summary,
        category=category,  # type: ignore[arg-type]
        source_ids=[source_id],
        claim_cluster_ids=[],
        confidence="medium",
        claim_type="reported_fact",
    )


def test_classify_tension_event_scores_escalation_and_deescalation():
    strike = event("strike", "2026-03-02", "Iran missile attack targets Israel", "Missile strikes and direct attack.", "wiki-ref:1")
    ceasefire = event("ceasefire", "2026-03-03", "US Iran ceasefire talks resume", "Peace talks and ceasefire proposal.", "wiki-ref:2")

    assert classify_tension_event(strike).delta > 0
    assert classify_tension_event(ceasefire).delta < 0


def test_build_tension_series_keeps_daily_source_ids_and_directional_movement():
    events = [
        event("strike", "2026-03-02", "Iran missile attack targets Israel", "Missile strikes and direct attack.", "wiki-ref:1"),
        event("ceasefire", "2026-03-04", "US Iran ceasefire talks resume", "Peace talks and ceasefire proposal.", "wiki-ref:2"),
    ]

    series = build_tension_series(events, start="2026-03-01", end="2026-03-05")
    by_date = {point.date: point for point in series}

    assert by_date["2026-03-02"].value > by_date["2026-03-01"].value
    assert by_date["2026-03-04"].value < by_date["2026-03-03"].value
    assert by_date["2026-03-02"].source_ids == ["wiki-ref:1"]
    assert by_date["2026-03-04"].source_ids == ["wiki-ref:2"]


def test_build_tension_series_decays_toward_neutral_on_quiet_days():
    events = [
        event("strike", "2026-03-02", "Iran missile attack targets Israel", "Missile strikes and direct attack.", "wiki-ref:1"),
    ]

    series = build_tension_series(events, start="2026-03-01", end="2026-03-06")
    by_date = {point.date: point for point in series}

    assert by_date["2026-03-03"].value < by_date["2026-03-02"].value
    assert by_date["2026-03-06"].value < by_date["2026-03-03"].value


def test_build_tension_series_ignores_background_corpus_events():
    events = [
        event(
            "background",
            "2025-12-01",
            "2026 Iran war - economic impacts",
            "Background discusses war, missile attacks, Hormuz risk, and sanctions as historical context.",
            "wiki:background",
            category="background",
        )
    ]

    series = build_tension_series(events, start="2025-12-01", end="2025-12-02")
    by_date = {point.date: point for point in series}

    assert by_date["2025-12-01"].value <= 45
    assert by_date["2025-12-01"].source_ids == []


def test_ceasefire_headline_is_not_overridden_by_generic_war_word():
    ceasefire = event(
        "ceasefire",
        "2026-03-03",
        "Trump announces Iran ceasefire extension to end the war",
        "Peace proposal and mediator talks continue without new strikes.",
        "wiki-ref:ceasefire",
        category="statement",
    )

    assert classify_tension_event(ceasefire).delta < 0


def test_duplicate_heavy_escalation_day_does_not_pin_series_at_ceiling():
    events = [
        event(
            f"strike-{index}",
            "2026-03-02",
            "Iran missile attack targets Israel",
            "Missile strikes and direct attack.",
            f"wiki-ref:{index}",
            category="strike",
        )
        for index in range(8)
    ]

    series = build_tension_series(events, start="2026-03-02", end="2026-03-03")
    by_date = {point.date: point for point in series}

    assert 45 < by_date["2026-03-02"].value < 80
    assert by_date["2026-03-03"].value < by_date["2026-03-02"].value


def test_sustained_escalation_stays_below_display_ceiling():
    events = [
        event(
            f"strike-{day}",
            f"2026-03-{day:02d}",
            "Iran missile attack targets Israel",
            "Missile attack and direct strikes continued.",
            f"wiki-ref:{day}",
            category="strike",
        )
        for day in range(1, 11)
    ]

    series = build_tension_series(events, start="2026-03-01", end="2026-03-12")
    values = [point.value for point in series]

    assert max(values) < 95
    assert values[2] > values[0]
    assert values[-1] < max(values)
