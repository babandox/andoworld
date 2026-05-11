from backend.app.iran_war.ingestion import (
    DEFAULT_INGEST_TIMEOUT_SECONDS,
    IngestedSourceBundle,
    _dedupe_bundle,
    _select_polymarket_history_records,
    build_gdelt_request_urls,
    build_fred_source_documents,
    build_polymarket_search_urls,
    extract_polymarket_search_records,
    ingest_gdelt,
    parse_gdelt_articles,
    parse_fred_observations,
    parse_polymarket_markets,
    parse_polymarket_price_history,
    polymarket_current_price_point,
    parse_polymarket_search_results,
    parse_wikipedia_page,
    parse_wikipedia_references_html,
)
from backend.app.iran_war.gdelt_raw import (
    RawGdeltArchiveResult,
    build_gdelt_source_documents,
    parse_gdelt_export_rows,
    parse_gdelt_masterfilelist,
    parse_gdelt_mentions_rows,
)
from backend.app.iran_war.persistence import PersistenceResult
from backend.app.iran_war.case_builder import build_case_from_ingestion
from backend.app.iran_war.source_status import build_source_status
from backend.app.models import PredictionMarketPricePoint, SourceDocument
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse


class FakeSection:
    def __init__(self, title: str, text: str, sections=None):
        self.title = title
        self.text = text
        self.sections = sections or []


class FakePage:
    title = "2026 Iran war"
    fullurl = "https://en.wikipedia.org/wiki/2026_Iran_war"
    pageid = 12345
    summary = "Summary text"
    sections = [
        FakeSection("Background", "Background text about nuclear issues and sanctions."),
        FakeSection("Military operations", "Operational details should not be preferred."),
    ]


def test_parse_wikipedia_page_extracts_relevant_sections_with_metadata():
    docs = parse_wikipedia_page(FakePage(), retrieved_at="2026-05-09", revision_id="rev-1")

    assert len(docs) == 1
    assert docs[0].source_type == "wikipedia"
    assert docs[0].section_title == "Background"
    assert docs[0].revision_id == "rev-1"
    assert "nuclear issues" in docs[0].excerpt


def test_parse_wikipedia_page_keeps_subsections_under_relevant_background_section():
    class PageWithNestedBackground:
        title = "2026 Iran war"
        fullurl = "https://en.wikipedia.org/wiki/2026_Iran_war"
        pageid = 12345
        summary = ""
        sections = [
            FakeSection(
                "Background",
                "Parent background.",
                sections=[FakeSection("1953 coup", "The 1953 coup shaped long-running US-Iran distrust.")],
            )
        ]

    docs = parse_wikipedia_page(PageWithNestedBackground(), retrieved_at="2026-05-10", revision_id="rev-2")

    assert any(doc.section_title == "1953 coup" and "US-Iran distrust" in doc.excerpt for doc in docs)


def test_parse_wikipedia_references_html_extracts_timestamped_news_citations():
    html = """
    <ol class="references">
      <li id="cite_note-one"><span class="reference-text">
        <style>.mw-parser-output .citation{font-size:inherit}</style>
        "Hezbollah claims responsibility for attack on Israel". <i>Al Jazeera English</i>. 2 March 2026. Retrieved 2 March 2026.
      </span></li>
      <li id="cite_note-two"><span class="reference-text">
        Diamond, Jeremy; Mezzofiore, Gianluca; Saifi, Zeena (12 March 2026).
        <a href="https://www.cnn.com/example">"How Iran's use of cluster munitions is challenging Israel's air defenses"</a>.
        CNN. Retrieved 18 March 2026.
      </span></li>
      <li id="cite_note-old"><span class="reference-text">
        "Old background article". Example. 6 June 2024. Retrieved 1 May 2026.
      </span></li>
    </ol>
    """

    docs = parse_wikipedia_references_html(
        "2026 Iran war",
        html,
        retrieved_at="2026-05-10",
        page_url="https://en.wikipedia.org/wiki/2026_Iran_war",
    )

    assert [doc.published_at for doc in docs] == ["2026-03-02", "2026-03-12"]
    assert docs[0].source_type == "wikipedia_reference"
    assert docs[0].title == "Hezbollah claims responsibility for attack on Israel"
    assert docs[1].url == "https://www.cnn.com/example"


def test_parse_fred_observations_discards_missing_values():
    payload = {
        "observations": [
            {"date": "2025-12-01", "value": "73.4"},
            {"date": "2025-12-02", "value": "."},
        ]
    }

    points = parse_fred_observations(payload, series="Brent")

    assert len(points) == 1
    assert points[0].series == "Brent"
    assert points[0].value == 73.4
    assert points[0].source == "FRED"


def test_build_fred_source_documents_cites_live_market_series():
    points = parse_fred_observations(
        {"observations": [{"date": "2025-12-01", "value": "73.4"}, {"date": "2025-12-02", "value": "74.1"}]},
        series="Brent",
    )

    docs = build_fred_source_documents(points, retrieved_at="2026-05-09")

    assert len(docs) == 1
    assert docs[0].source_type == "fred"
    assert docs[0].id == "fred:brent"
    assert "2 observations" in docs[0].excerpt
    assert "fred.stlouisfed.org" in str(docs[0].url)


def test_parse_polymarket_markets_includes_closed_and_active_signals():
    payload = [
        {
            "id": "m1",
            "question": "Will Iran close the Strait of Hormuz?",
            "closed": True,
            "endDate": "2026-03-05T00:00:00Z",
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0","1"]',
            "url": "https://polymarket.com/event/iran-hormuz",
        },
        {
            "id": "m2",
            "question": "Will there be an Iran ceasefire?",
            "closed": False,
            "endDate": "2026-05-31T00:00:00Z",
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0.44","0.56"]',
        },
    ]

    docs = parse_polymarket_markets(payload, retrieved_at="2026-05-09")

    assert len(docs) == 2
    assert docs[0].source_type == "polymarket"
    assert "closed" in docs[0].excerpt.lower()
    assert "44.0%" in docs[1].excerpt


def test_parse_polymarket_markets_rejects_unrelated_and_old_records():
    payload = [
        {
            "id": "unrelated",
            "question": "New Rihanna Album before GTA VI?",
            "endDate": "2026-07-31T12:00:00Z",
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0.5","0.5"]',
        },
        {
            "id": "old",
            "question": "Will Iran close the Strait of Hormuz?",
            "endDate": "2020-11-04T00:00:00Z",
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0","1"]',
        },
        {
            "id": "current",
            "question": "Will Iran close the Strait of Hormuz in 2026?",
            "endDate": "2026-05-31T00:00:00Z",
            "outcomes": '["Yes","No"]',
            "outcomePrices": '["0.12","0.88"]',
        },
    ]

    docs = parse_polymarket_markets(payload, retrieved_at="2026-05-09")

    assert [doc.id for doc in docs] == ["polymarket:current"]


def test_parse_polymarket_search_results_reads_public_search_events():
    payload = {
        "events": [
            {
                "id": "event-iran",
                "title": "US x Iran permanent peace deal by...?",
                "slug": "us-x-iran-permanent-peace-deal-by",
                "endDate": "2026-12-31T00:00:00Z",
                "markets": [
                    {
                        "id": "nested",
                        "question": "US x Iran permanent peace deal by May 31, 2026?",
                        "endDate": "2026-05-31T00:00:00Z",
                        "outcomes": '["Yes","No"]',
                        "outcomePrices": '["0.285","0.715"]',
                    }
                ],
            },
            {
                "id": "event-noise",
                "title": "New Rihanna Album before GTA VI?",
                "endDate": "2026-07-31T12:00:00Z",
                "markets": [],
            },
        ]
    }

    docs = parse_polymarket_search_results(payload, retrieved_at="2026-05-09")

    assert len(docs) == 1
    assert docs[0].id == "polymarket:nested"
    assert "28.5%" in docs[0].excerpt


def test_extract_polymarket_search_records_preserves_clob_token_ids_for_history():
    payload = {
        "events": [
            {
                "id": "event-iran",
                "title": "US x Iran permanent peace deal by...?",
                "slug": "us-x-iran-permanent-peace-deal-by",
                "markets": [
                    {
                        "id": "nested",
                        "question": "US x Iran permanent peace deal by May 31, 2026?",
                        "startDate": "2026-04-08T16:16:14Z",
                        "endDate": "2026-05-31T00:00:00Z",
                        "clobTokenIds": '["yes-token","no-token"]',
                        "outcomes": '["Yes","No"]',
                        "outcomePrices": '["0.285","0.715"]',
                    }
                ],
            }
        ]
    }

    records = extract_polymarket_search_records(payload)

    assert len(records) == 1
    assert records[0]["id"] == "nested"
    assert records[0]["clobTokenIds"] == '["yes-token","no-token"]'
    assert records[0]["outcomes"] == '["Yes","No"]'


def test_parse_polymarket_price_history_returns_daily_close_probabilities():
    record = {
        "id": "m1",
        "question": "Will Iran close the Strait of Hormuz in May?",
        "closed": True,
        "startDate": "2026-04-08T16:16:14Z",
        "closedTime": "2026-04-10 07:34:32+00",
        "slug": "iran-close-hormuz-may",
    }
    payload = {
        "history": [
            {"t": int(datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc).timestamp()), "p": 0.12},
            {"t": int(datetime(2026, 4, 8, 23, 59, tzinfo=timezone.utc).timestamp()), "p": 0.18},
            {"t": int(datetime(2026, 4, 9, 23, 59, tzinfo=timezone.utc).timestamp()), "p": 0.04},
        ]
    }

    points = parse_polymarket_price_history(payload, record=record, token_id="yes-token", outcome="Yes")

    assert [(point.date, point.probability) for point in points] == [("2026-04-08", 0.18), ("2026-04-09", 0.04)]
    assert points[0].market_id == "m1"
    assert points[0].status == "resolved"
    assert points[0].market_start == "2026-04-08"
    assert points[0].market_end == "2026-04-10"
    assert points[0].url == "https://polymarket.com/event/iran-close-hormuz-may"


def test_polymarket_current_price_point_falls_back_when_history_is_unavailable():
    record = {
        "id": "m1",
        "question": "Will Iran close the Strait of Hormuz in May?",
        "closed": False,
        "active": True,
        "startDate": "2026-05-08T16:16:14Z",
        "endDate": "2026-05-31T00:00:00Z",
        "updatedAt": "2026-05-10T12:00:00Z",
        "slug": "iran-close-hormuz-may",
        "outcomes": '["Yes","No"]',
        "outcomePrices": '["0.27","0.73"]',
    }

    point = polymarket_current_price_point(record, token_id="yes-token", outcome="Yes")

    assert point is not None
    assert point.date == "2026-05-10"
    assert point.probability == 0.27
    assert point.status == "active"


def test_polymarket_history_selection_includes_resolved_markets_across_window():
    records = [
        {
            "id": f"active-{index}",
            "question": f"Will WTI crude oil hit ${110 + index} in May?",
            "closed": False,
            "active": True,
            "startDate": f"2026-05-0{index + 1}T00:00:00Z",
            "endDate": "2026-05-31T00:00:00Z",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        }
        for index in range(5)
    ] + [
        {
            "id": "resolved-december",
            "question": "Will Iran close the Strait of Hormuz in December?",
            "closed": True,
            "startDate": "2025-12-26T00:00:00Z",
            "closedTime": "2025-12-31 18:00:00+00",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        },
        {
            "id": "resolved-march",
            "question": "Will there be an Iran ceasefire by March 31?",
            "closed": True,
            "startDate": "2026-03-01T00:00:00Z",
            "closedTime": "2026-03-31 18:00:00+00",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        },
        {
            "id": "old-updated-market",
            "question": "Will Iran close the Strait of Hormuz in 2024?",
            "closed": True,
            "startDate": "2024-08-01T00:00:00Z",
            "endDate": "2024-09-01T00:00:00Z",
            "updatedAt": "2026-05-10T00:00:00Z",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        },
    ]

    selected = _select_polymarket_history_records(records, limit=4)

    selected_ids = {record["id"] for record in selected}
    assert "resolved-december" in selected_ids
    assert "resolved-march" in selected_ids
    assert "old-updated-market" not in selected_ids
    assert any(record["id"].startswith("active-") for record in selected)


def test_polymarket_history_selection_rejects_word_count_and_repetitive_warship_markets():
    records = [
        {
            "id": "word-count",
            "question": 'Will Trump say "Iran" or "Nuclear" 5+ times during the Hanukkah Reception event on Tuesday?',
            "closed": True,
            "startDate": "2025-12-16T00:00:00Z",
            "closedTime": "2025-12-17 18:00:00+00",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        },
        {
            "id": "warships",
            "question": "Will France send warships through the Strait of Hormuz by May 31, 2026?",
            "closed": False,
            "startDate": "2026-05-06T00:00:00Z",
            "endDate": "2026-05-31T00:00:00Z",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        },
        {
            "id": "scenario",
            "question": "Will Iran close the Strait of Hormuz by March 31?",
            "closed": True,
            "startDate": "2026-01-20T00:00:00Z",
            "closedTime": "2026-03-14 18:00:00+00",
            "clobTokenIds": '["yes","no"]',
            "outcomes": '["Yes","No"]',
        },
    ]

    selected = _select_polymarket_history_records(records, limit=8)

    assert [record["id"] for record in selected] == ["scenario"]


def test_polymarket_search_urls_request_enough_results_for_resolved_markets():
    urls = build_polymarket_search_urls()

    assert urls
    for url in urls:
        params = parse_qs(urlparse(url).query)
        assert params["keep_closed_markets"] == ["1"]
        assert int(params["limit_per_type"][0]) >= 50


def test_gdelt_request_builder_uses_windowed_date_queries_not_latest_timespan():
    urls = build_gdelt_request_urls(max_records=50, now="2026-05-10T12:00:00Z")

    assert len(urls) > 1
    assert all("api.gdeltproject.org/api/v2/doc/doc" in url for url in urls)
    assert all("mode=artlist" in url for url in urls)
    assert all("format=json" in url for url in urls)
    assert all("startdatetime=" in url and "enddatetime=" in url for url in urls)
    assert all("timespan=" not in url.lower() for url in urls)
    assert "startdatetime=202602" in urls[0]


def test_gdelt_request_builder_uses_dense_recent_windows_with_large_record_budget():
    urls = build_gdelt_request_urls(now="2026-05-10T12:00:00Z")

    assert len(urls) >= 10
    for url in urls:
        params = parse_qs(urlparse(url).query)
        assert params["maxrecords"] == ["250"]
        start = datetime.strptime(params["startdatetime"][0], "%Y%m%d%H%M%S")
        end = datetime.strptime(params["enddatetime"][0], "%Y%m%d%H%M%S")
        assert (end - start).days <= 7


def test_default_ingestion_timeout_allows_slow_gdelt_doc_responses():
    assert DEFAULT_INGEST_TIMEOUT_SECONDS >= 15


def test_parse_gdelt_articles_filters_to_relevant_iran_records():
    payload = {
        "articles": [
            {
                "url": "https://example.test/rihanna",
                "title": "New Rihanna Album before GTA VI?",
                "seendate": "20260508120000",
                "domain": "example.test",
            },
            {
                "url": "https://example.test/hormuz",
                "title": "Oil rises as Iran tensions put Strait of Hormuz in focus",
                "seendate": "20260508130000",
                "domain": "example.test",
            },
            {
                "url": "https://example.test/iran",
                "title": "     ,     - ",
                "seendate": "20260508140000",
                "domain": "example.test",
            },
        ]
    }

    docs = parse_gdelt_articles(payload, retrieved_at="2026-05-09", query="Iran")

    assert len(docs) == 1
    assert "Hormuz" in docs[0].title


def test_parse_gdelt_articles_collapses_duplicate_titles_from_syndication():
    payload = {
        "articles": [
            {
                "url": "https://wire-a.test/iran-warning",
                "title": "Iran warns US against attacks on ships",
                "seendate": "20260509221500",
                "domain": "wire-a.test",
            },
            {
                "url": "https://wire-b.test/iran-warning-copy",
                "title": "Iran warns US against attacks on ships",
                "seendate": "20260509221800",
                "domain": "wire-b.test",
            },
        ]
    }

    docs = parse_gdelt_articles(payload, retrieved_at="2026-05-10", query="Iran")

    assert len(docs) == 1
    assert docs[0].url == "https://wire-a.test/iran-warning"


def test_dedupe_bundle_collapses_gdelt_duplicate_titles_across_queries():
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="gdelt:a",
                source_type="gdelt",
                title="Iran warns US against attacks on ships",
                url="https://wire-a.test/iran-warning",
                published_at="20260509221500",
                retrieved_at="2026-05-10",
                excerpt="First record.",
            ),
            SourceDocument(
                id="gdelt:b",
                source_type="gdelt",
                title="Iran warns US against attacks on ships",
                url="https://wire-b.test/iran-warning-copy",
                published_at="20260509221800",
                retrieved_at="2026-05-10",
                excerpt="Duplicate record.",
            ),
        ]
    )

    deduped = _dedupe_bundle(bundle)

    assert [source.id for source in deduped.source_documents] == ["gdelt:a"]


def test_case_builder_prefers_live_ingestion_sources_over_fixture_only_case():
    bundle = IngestedSourceBundle(
        source_documents=parse_wikipedia_page(FakePage(), retrieved_at="2026-05-09", revision_id="rev-1"),
        market_series=parse_fred_observations({"observations": [{"date": "2025-12-01", "value": "73.4"}]}, series="Brent"),
        market_markers=[],
    )

    case = build_case_from_ingestion(bundle)

    assert any(source.source_type == "wikipedia" and source.revision_id == "rev-1" for source in case.source_documents)
    assert not any(source.source_type == "statement_archive" for source in case.source_documents)
    assert any(point.source == "FRED" for point in case.market_series)
    assert "live source ingestion" in case.summary.lower()
    assert case.source_status.wikipedia.available is True
    assert case.source_status.gdelt.available is False
    assert case.source_status.polymarket.available is False
    assert case.source_status.fred.available is True
    assert any("Iran nuclear issue" in node.label for node in case.graph_view.nodes)
    assert case.atomic_claims
    assert case.claim_clusters
    assert case.claim_contradictions == []


def test_case_builder_surfaces_adapter_errors_in_source_status_notes(monkeypatch):
    monkeypatch.setattr("backend.app.iran_war.case_builder.load_cached_source_documents", lambda source_type, limit=100: [])
    bundle = IngestedSourceBundle(errors=["GDELT DOC query failed: HTTP 429"])

    case = build_case_from_ingestion(bundle)

    assert case.source_status.gdelt.available is False
    assert "HTTP 429" in case.source_status.gdelt.note


def test_case_builder_uses_cached_gdelt_sources_when_live_gdelt_returns_none(monkeypatch):
    cached_gdelt = SourceDocument(
        id="gdelt:cached",
        source_type="gdelt",
        title="Cached Iran ceasefire report",
        url="https://example.test/cached",
        published_at="20260408120000",
        retrieved_at="2026-05-09",
        excerpt="Cached GDELT record.",
    )
    monkeypatch.setattr(
        "backend.app.iran_war.case_builder.load_cached_source_documents",
        lambda source_type, limit=100: [cached_gdelt] if source_type == "gdelt" else [],
    )

    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:background",
                source_type="wikipedia",
                title="2026 Iran war - Background",
                retrieved_at="2026-05-10",
                section_title="Background",
                excerpt="The background included the Iran nuclear program.",
            )
        ],
        errors=["GDELT DOC query failed: HTTP 429"],
    )

    case = build_case_from_ingestion(bundle)

    assert any(source.id == "gdelt:cached" for source in case.source_documents)
    assert case.source_status.gdelt.available is True
    assert "cached" in case.source_status.gdelt.note.lower()


def test_case_builder_keeps_prediction_and_market_sources_out_of_case_timeline():
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:background",
                source_type="wikipedia",
                title="2026 Iran war - Background",
                retrieved_at="2026-05-10",
                section_title="Background",
                excerpt="Historical background.",
            ),
            SourceDocument(
                id="gdelt:test",
                source_type="gdelt",
                title="Iran warns US against attacks on ships",
                url="https://example.test/iran",
                published_at="20260509221500",
                retrieved_at="2026-05-10",
                excerpt="GDELT news record.",
            ),
            SourceDocument(
                id="polymarket:test",
                source_type="polymarket",
                title="US x Iran permanent peace deal by May 31, 2026?",
                url="https://polymarket.com/event/test",
                published_at="2026-05-31T00:00:00Z",
                retrieved_at="2026-05-10",
                excerpt="Prediction-market signal.",
            ),
            SourceDocument(
                id="fred:test",
                source_type="fred",
                title="FRED WTI daily series",
                url="https://fred.stlouisfed.org/series/DCOILWTICO",
                published_at="2026-05-04",
                retrieved_at="2026-05-10",
                excerpt="Market data signal.",
            ),
        ]
    )

    case = build_case_from_ingestion(bundle)

    timeline_source_ids = {source_id for event in case.timeline_events for source_id in event.source_ids}
    assert "wiki:test:background" in timeline_source_ids
    assert "gdelt:test" in timeline_source_ids
    assert "polymarket:test" not in timeline_source_ids
    assert "fred:test" not in timeline_source_ids


def test_case_builder_carries_prediction_market_history_separately_from_sources():
    point = PredictionMarketPricePoint(
        market_id="m1",
        question="Will Iran close the Strait of Hormuz in May?",
        token_id="yes-token",
        outcome="Yes",
        date="2026-04-08",
        probability=0.18,
        status="resolved",
        source="Polymarket",
        market_start="2026-04-08",
        market_end="2026-04-10",
        url="https://polymarket.com/event/iran-close-hormuz-may",
    )
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:background",
                source_type="wikipedia",
                title="2026 Iran war - Background",
                retrieved_at="2026-05-10",
                section_title="Background",
                excerpt="Historical background.",
            ),
        ],
        prediction_market_series=[point],
    )

    case = build_case_from_ingestion(bundle)

    assert case.prediction_market_series == [point]
    assert all(event.claim_type != "market_expectation" for event in case.timeline_events)


def test_case_builder_extracts_wikipedia_event_dates_for_timeline_anchors():
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:1953-coup",
                source_type="wikipedia",
                title="2026 Iran war - 1953 coup",
                retrieved_at="2026-05-10",
                section_title="1953 coup",
                excerpt="The 1953 coup shaped later distrust.",
            ),
            SourceDocument(
                id="wiki:test:failed-talks",
                source_type="wikipedia",
                title="2026 Iran war - Failed talks",
                retrieved_at="2026-05-10",
                section_title="Failed talks",
                excerpt="On 18 February 2026, nuclear talks failed after the latest proposal was rejected.",
            ),
        ]
    )

    case = build_case_from_ingestion(bundle)
    dates_by_source = {event.source_ids[0]: event.occurred_at for event in case.timeline_events}

    assert dates_by_source["wiki:test:1953-coup"] == "1953-01-01"
    assert dates_by_source["wiki:test:failed-talks"] == "2026-02-18"


def test_case_builder_keeps_later_wikipedia_reference_events_when_reference_volume_is_high():
    sources = [
        SourceDocument(
            id="wiki:test:background",
            source_type="wikipedia",
            title="2026 Iran war - Background",
            retrieved_at="2026-05-10",
            section_title="Background",
            excerpt="Historical background.",
        )
    ]
    sources.extend(
        SourceDocument(
            id=f"wiki-ref:jan-{index}",
            source_type="wikipedia_reference",
            title=f"January report {index}",
            published_at=f"2026-01-{(index % 28) + 1:02d}",
            retrieved_at="2026-05-10",
            section_title="References",
            excerpt="January citation.",
        )
        for index in range(420)
    )
    sources.append(
        SourceDocument(
            id="wiki-ref:may-critical",
            source_type="wikipedia_reference",
            title="Iran warns US against attacks on ships",
            published_at="2026-05-09",
            retrieved_at="2026-05-10",
            section_title="References",
            excerpt="May citation.",
        )
    )

    case = build_case_from_ingestion(IngestedSourceBundle(source_documents=sources))

    timeline_source_ids = {source_id for event in case.timeline_events for source_id in event.source_ids}
    assert "wiki-ref:may-critical" in timeline_source_ids


def test_case_builder_does_not_use_wikipedia_article_title_as_event_date():
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:generic-background",
                source_type="wikipedia",
                title="2026 Iran war - Background",
                retrieved_at="2026-05-10",
                section_title="Background",
                excerpt="This section summarizes long-running historical context without a specific date.",
            )
        ]
    )

    case = build_case_from_ingestion(bundle)

    assert case.timeline_events[0].occurred_at == "2025-12-01"


def test_case_builder_uses_wikipedia_to_build_causal_driver_graph_not_source_buckets():
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:background",
                source_type="wikipedia",
                title="2026 Iran war - Background",
                retrieved_at="2026-05-10",
                section_title="Background",
                excerpt=(
                    "The background included the 1953 coup, the 1979 Iranian Revolution, "
                    "sanctions, the Iran nuclear program, the JCPOA collapse, and the Iran-Israel shadow conflict."
                ),
            ),
            SourceDocument(
                id="wiki:test:rationale",
                source_type="wikipedia",
                title="Rationale for the 2026 Iran war - US rationale",
                retrieved_at="2026-05-10",
                section_title="US rationale",
                excerpt="US and Israeli rationales emphasized nuclear risk, deterrence, and regional security.",
            ),
            SourceDocument(
                id="wiki:test:energy",
                source_type="wikipedia",
                title="2026 Iran war - Energy",
                retrieved_at="2026-05-10",
                section_title="Energy",
                excerpt="The war threatened the Strait of Hormuz and raised global oil supply risks.",
            ),
            SourceDocument(
                id="gdelt:test",
                source_type="gdelt",
                title="Iran warns US against attacks on ships",
                url="https://example.test/iran",
                published_at="20260509221500",
                retrieved_at="2026-05-10",
                excerpt="GDELT news record.",
            ),
            SourceDocument(
                id="polymarket:test",
                source_type="polymarket",
                title="US x Iran permanent peace deal by May 31, 2026?",
                retrieved_at="2026-05-10",
                excerpt="Prediction-market signal.",
            ),
            SourceDocument(
                id="fred:test",
                source_type="fred",
                title="FRED WTI daily series",
                retrieved_at="2026-05-10",
                excerpt="Market data signal.",
            ),
        ]
    )

    case = build_case_from_ingestion(bundle)
    labels = {node.label for node in case.graph_view.nodes}

    assert "1953 coup and long-run US-Iran distrust" in labels
    assert "Iran nuclear issue and JCPOA collapse" in labels
    assert "Polymarket Iran markets" not in labels
    assert "FRED market series" not in labels
    assert case.claim_clusters
    assert all(cluster.id in {claim.claim_cluster_ids[0] for claim in case.graph_view.nodes if claim.claim_cluster_ids} for cluster in case.claim_clusters)
    assert all(source.source_node_id != "node:live-polymarket-expectations" for source in case.graph_view.edges)


def test_case_builder_exposes_extraction_method_and_storage_results(monkeypatch):
    bundle = IngestedSourceBundle(
        source_documents=[
            SourceDocument(
                id="wiki:test:background",
                source_type="wikipedia",
                title="2026 Iran war - Background",
                retrieved_at="2026-05-10",
                section_title="Background",
                excerpt="The background included sanctions and the Iran nuclear program.",
            )
        ]
    )

    monkeypatch.setattr(
        "backend.app.iran_war.case_builder.persist_case_artifacts",
        lambda case: PersistenceResult(
            postgres_available=True,
            qdrant_available=True,
            postgres_note="Persisted 1 source document to Postgres.",
            qdrant_note="Indexed 1 source document in Qdrant.",
        ),
    )

    case = build_case_from_ingestion(bundle)

    assert case.extraction_status.method == "deterministic-wikipedia-fallback"
    assert "Wikipedia" in case.extraction_status.note
    assert case.source_status.postgres.available is True
    assert case.source_status.qdrant.available is True
    assert "Persisted" in case.source_status.postgres.note
    assert "Indexed" in case.source_status.qdrant.note


def test_source_status_tries_local_postgres_and_qdrant_defaults_when_urls_are_unset(monkeypatch):
    checked_urls: list[str] = []

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.setattr(
        "backend.app.iran_war.source_status._can_connect_url",
        lambda url: checked_urls.append(url) or True,
    )

    status = build_source_status()

    assert status.postgres.configured is False
    assert status.postgres.available is True
    assert status.qdrant.configured is False
    assert status.qdrant.available is True
    assert any(url.startswith("postgresql://") for url in checked_urls)
    assert any(url.startswith("http://127.0.0.1:6333") for url in checked_urls)


def gdelt_export_row(
    *,
    event_id: str,
    sql_date: str,
    actor1_name: str,
    actor1_country: str,
    actor2_name: str,
    actor2_country: str,
    event_code: str,
    event_root: str,
    quad_class: str,
    source_url: str,
) -> str:
    columns = [""] * 61
    columns[0] = event_id
    columns[1] = sql_date
    columns[5] = actor1_country
    columns[6] = actor1_name
    columns[7] = actor1_country
    columns[15] = actor2_country
    columns[16] = actor2_name
    columns[17] = actor2_country
    columns[26] = event_code
    columns[27] = event_code[:3]
    columns[28] = event_root
    columns[29] = quad_class
    columns[30] = "-7.2"
    columns[31] = "12"
    columns[32] = "3"
    columns[33] = "4"
    columns[34] = "-4.5"
    columns[36] = actor1_name
    columns[37] = actor1_country
    columns[43] = actor2_name
    columns[44] = actor2_country
    columns[50] = actor2_name
    columns[51] = actor2_country
    columns[59] = f"{sql_date}120000"
    columns[60] = source_url
    return "\t".join(columns)


def gdelt_mention_row(event_id: str, mention_time: str, source_name: str, url: str) -> str:
    columns = [""] * 16
    columns[0] = event_id
    columns[1] = mention_time
    columns[2] = mention_time
    columns[4] = source_name
    columns[5] = url
    columns[11] = "85"
    columns[13] = "-5.2"
    return "\t".join(columns)


def test_gdelt_raw_manifest_parser_selects_export_and_mentions_files_in_window():
    manifest = """
    38197 f3b88fd0334517c4de87e3eb8baf099b http://data.gdeltproject.org/gdeltv2/20260510220000.export.CSV.zip
    67483 0e684ed43bb7f3e9463a31f932c31be1 http://data.gdeltproject.org/gdeltv2/20260510220000.mentions.CSV.zip
    2548929 8bff950a9d471b03fe0e8d124d232005 http://data.gdeltproject.org/gdeltv2/20260510220000.gkg.csv.zip
    39726 f565dec8b8a61a6e55631a7b97373419 http://data.gdeltproject.org/gdeltv2/20260511221500.export.CSV.zip
    """

    files = parse_gdelt_masterfilelist(
        manifest,
        start="2026-05-10",
        end="2026-05-10",
        file_types={"export", "mentions"},
    )

    assert [(file.timestamp, file.file_type) for file in files] == [
        ("20260510220000", "export"),
        ("20260510220000", "mentions"),
    ]


def test_gdelt_raw_export_parser_filters_to_iran_conflict_events():
    export_text = "\n".join(
        [
            gdelt_export_row(
                event_id="1",
                sql_date="20260302",
                actor1_name="IRAN",
                actor1_country="IRN",
                actor2_name="ISRAEL",
                actor2_country="ISR",
                event_code="190",
                event_root="19",
                quad_class="4",
                source_url="https://example.test/iran-missile-strike-israel",
            ),
            gdelt_export_row(
                event_id="2",
                sql_date="20260302",
                actor1_name="RIHANNA",
                actor1_country="USA",
                actor2_name="MUSIC INDUSTRY",
                actor2_country="USA",
                event_code="010",
                event_root="01",
                quad_class="1",
                source_url="https://example.test/rihanna-album",
            ),
        ]
    )

    events = parse_gdelt_export_rows(export_text)

    assert [event.event_id for event in events] == ["1"]
    assert events[0].actor1_name == "IRAN"
    assert events[0].actor2_country_code == "ISR"
    assert events[0].source_url == "https://example.test/iran-missile-strike-israel"


def test_gdelt_raw_export_parser_rejects_weak_iran_mentions_without_conflict_topic():
    export_text = gdelt_export_row(
        event_id="weak",
        sql_date="20260510",
        actor1_name="ADMINISTRATION",
        actor1_country="USA",
        actor2_name="IRAN",
        actor2_country="IRN",
        event_code="010",
        event_root="01",
        quad_class="1",
        source_url="https://example.test/trump-economy-broken-twice-covid-china-tariffs",
    )

    assert parse_gdelt_export_rows(export_text) == []


def test_gdelt_raw_export_parser_rejects_loose_iran_actor_without_conflict_topic():
    export_text = gdelt_export_row(
        event_id="loose",
        sql_date="20251201",
        actor1_name="IRAN",
        actor1_country="IRN",
        actor2_name="TURKEY",
        actor2_country="TUR",
        event_code="046",
        event_root="04",
        quad_class="1",
        source_url="https://example.test/weekend-news-roundup-asia-market-open",
    )

    assert parse_gdelt_export_rows(export_text) == []


def test_gdelt_raw_export_parser_rejects_secondary_geocode_only_iran_signal():
    columns = gdelt_export_row(
        event_id="geo-noise",
        sql_date="20251201",
        actor1_name="SHIRAZ",
        actor1_country="AUS",
        actor2_name="SOUTH AUSTRALIA",
        actor2_country="AUS",
        event_code="051",
        event_root="05",
        quad_class="1",
        source_url="https://example.test/heritage-inspired-wine-gifts",
    ).split("\t")
    columns[44] = "USA"
    columns[51] = "IRN"

    assert parse_gdelt_export_rows("\t".join(columns)) == []


def test_gdelt_raw_export_parser_keeps_iran_oil_tanker_attack_signal():
    export_text = gdelt_export_row(
        event_id="tanker",
        sql_date="20251201",
        actor1_name="IRAN",
        actor1_country="IRN",
        actor2_name="TANKER",
        actor2_country="",
        event_code="190",
        event_root="19",
        quad_class="4",
        source_url="https://example.test/brit-dad-killed-iranian-drone-oil-tanker",
    )

    events = parse_gdelt_export_rows(export_text)

    assert [event.event_id for event in events] == ["tanker"]
    assert events[0].signal_family == "direct_conflict_signal"
    assert events[0].forecast_direction == "escalatory"


def test_gdelt_raw_export_parser_classifies_iran_economic_pressure_signal():
    export_text = gdelt_export_row(
        event_id="economy",
        sql_date="20251208",
        actor1_name="IRAN",
        actor1_country="IRN",
        actor2_name="SANCTIONS",
        actor2_country="USA",
        event_code="046",
        event_root="04",
        quad_class="1",
        source_url="https://example.test/iran-economy-sanctions-oil-revenue-pressure",
    )

    events = parse_gdelt_export_rows(export_text)

    assert [event.event_id for event in events] == ["economy"]
    assert events[0].signal_family == "economic_pressure_signal"
    assert events[0].forecast_direction == "escalatory"
    assert events[0].signal_strength >= 2


def test_gdelt_raw_export_parser_classifies_us_political_and_diplomacy_signals():
    export_text = "\n".join(
        [
            gdelt_export_row(
                event_id="us-politics",
                sql_date="20260115",
                actor1_name="TRUMP",
                actor1_country="USA",
                actor2_name="IRAN",
                actor2_country="IRN",
                event_code="042",
                event_root="04",
                quad_class="1",
                source_url="https://example.test/trump-iran-congress-white-house-nuclear-strategy",
            ),
            gdelt_export_row(
                event_id="talks",
                sql_date="20260202",
                actor1_name="IRAN",
                actor1_country="IRN",
                actor2_name="UNITED STATES",
                actor2_country="USA",
                event_code="050",
                event_root="05",
                quad_class="1",
                source_url="https://example.test/iran-us-nuclear-talks-ceasefire-proposal",
            ),
        ]
    )

    events = parse_gdelt_export_rows(export_text)

    assert [event.signal_family for event in events] == ["us_political_signal", "diplomacy_signal"]
    assert events[0].forecast_direction == "uncertain"
    assert events[1].forecast_direction == "deescalatory"


def test_gdelt_raw_export_parser_keeps_iran_background_context_when_url_is_about_iran():
    export_text = gdelt_export_row(
        event_id="background",
        sql_date="20251211",
        actor1_name="IRAN",
        actor1_country="IRN",
        actor2_name="ANALYSTS",
        actor2_country="",
        event_code="010",
        event_root="01",
        quad_class="1",
        source_url="https://example.test/iran-regime-nuclear-program-background-explainer",
    )

    events = parse_gdelt_export_rows(export_text)

    assert [event.event_id for event in events] == ["background"]
    assert events[0].signal_family == "background_context"
    assert events[0].forecast_direction == "background"


def test_gdelt_raw_mentions_join_into_source_documents():
    events = parse_gdelt_export_rows(
        gdelt_export_row(
            event_id="1",
            sql_date="20260302",
            actor1_name="IRAN",
            actor1_country="IRN",
            actor2_name="UNITED STATES",
            actor2_country="USA",
            event_code="130",
            event_root="13",
            quad_class="3",
            source_url="https://wire.test/iran-warns-us",
        )
    )
    mentions = parse_gdelt_mentions_rows(
        gdelt_mention_row("1", "20260302141500", "wire.test", "https://wire.test/iran-warns-us"),
        event_ids={"1"},
    )

    docs = build_gdelt_source_documents(events, mentions, retrieved_at="2026-05-11")

    assert len(docs) == 1
    assert docs[0].source_type == "gdelt"
    assert docs[0].url == "https://wire.test/iran-warns-us"
    assert docs[0].published_at == "20260302141500"
    assert "EventCode 130" in docs[0].excerpt
    assert "SignalFamily rhetoric_signal" in docs[0].excerpt
    assert "ForecastDirection escalatory" in docs[0].excerpt
    assert "UNITED STATES" in docs[0].excerpt


def test_gdelt_raw_documents_collapse_duplicate_titles_from_syndication():
    events = parse_gdelt_export_rows(
        "\n".join(
            [
                gdelt_export_row(
                    event_id="1",
                    sql_date="20260302",
                    actor1_name="IRAN",
                    actor1_country="IRN",
                    actor2_name="UNITED STATES",
                    actor2_country="USA",
                    event_code="130",
                    event_root="13",
                    quad_class="3",
                    source_url="https://wire-a.test/iran-warns-us",
                ),
                gdelt_export_row(
                    event_id="2",
                    sql_date="20260302",
                    actor1_name="IRAN",
                    actor1_country="IRN",
                    actor2_name="UNITED STATES",
                    actor2_country="USA",
                    event_code="130",
                    event_root="13",
                    quad_class="3",
                    source_url="https://wire-b.test/iran-warns-us",
                ),
            ]
        )
    )
    mentions = {
        "1": [parse_gdelt_mentions_rows(gdelt_mention_row("1", "20260302141500", "wire-a.test", "https://wire-a.test/iran-warns-us"), event_ids={"1"})["1"][0]],
        "2": [parse_gdelt_mentions_rows(gdelt_mention_row("2", "20260302141600", "wire-b.test", "https://wire-b.test/iran-warns-us"), event_ids={"2"})["2"][0]],
    }

    docs = build_gdelt_source_documents(events, mentions, retrieved_at="2026-05-11")

    assert len(docs) == 1
    assert docs[0].url == "https://wire-a.test/iran-warns-us"


def test_gdelt_raw_document_ids_are_stable_by_url_across_event_ids():
    first = build_gdelt_source_documents(
        parse_gdelt_export_rows(
            gdelt_export_row(
                event_id="1",
                sql_date="20260302",
                actor1_name="IRAN",
                actor1_country="IRN",
                actor2_name="ISRAEL",
                actor2_country="ISR",
                event_code="190",
                event_root="19",
                quad_class="4",
                source_url="https://wire.test/iran-missile-strike-israel",
            )
        ),
        {},
        retrieved_at="2026-05-11",
    )[0]
    second = build_gdelt_source_documents(
        parse_gdelt_export_rows(
            gdelt_export_row(
                event_id="2",
                sql_date="20260302",
                actor1_name="IRAN",
                actor1_country="IRN",
                actor2_name="ISRAEL",
                actor2_country="ISR",
                event_code="190",
                event_root="19",
                quad_class="4",
                source_url="https://wire.test/iran-missile-strike-israel",
            )
        ),
        {},
        retrieved_at="2026-05-11",
    )[0]

    assert first.id == second.id


def test_ingest_gdelt_prefers_raw_archive_documents(monkeypatch):
    raw_doc = SourceDocument(
        id="gdelt:raw",
        source_type="gdelt",
        title="Iran missile strike report",
        url="https://example.test/raw",
        published_at="20260302141500",
        retrieved_at="2026-05-11",
        excerpt="Raw GDELT archive match.",
    )
    monkeypatch.setattr(
        "backend.app.iran_war.ingestion.ingest_gdelt_raw_archive",
        lambda **kwargs: RawGdeltArchiveResult(source_documents=[raw_doc], errors=["GDELT raw archive one file failed"]),
    )
    monkeypatch.setattr("backend.app.iran_war.ingestion.build_gdelt_request_urls", lambda max_records: [])

    bundle = ingest_gdelt(retrieved_at="2026-05-11", timeout=1.0)

    assert bundle.source_documents == [raw_doc]
    assert bundle.errors == ["GDELT raw archive one file failed"]


def test_ingest_gdelt_falls_back_to_doc_api_when_raw_archive_has_no_matches(monkeypatch):
    monkeypatch.setattr(
        "backend.app.iran_war.ingestion.ingest_gdelt_raw_archive",
        lambda **kwargs: RawGdeltArchiveResult(errors=["GDELT raw archive found no matches"]),
    )
    monkeypatch.setattr("backend.app.iran_war.ingestion.build_gdelt_request_urls", lambda max_records: ["https://api.gdelt.test/doc"])
    monkeypatch.setattr(
        "backend.app.iran_war.ingestion._get_json",
        lambda url, timeout, retries=0, retry_pause_seconds=1.5: {
            "articles": [
                {
                    "url": "https://example.test/hormuz",
                    "title": "Oil rises as Iran tensions put Strait of Hormuz in focus",
                    "seendate": "20260508130000",
                    "domain": "example.test",
                }
            ]
        },
    )
    monkeypatch.setattr("backend.app.iran_war.ingestion.time.sleep", lambda seconds: None)

    bundle = ingest_gdelt(retrieved_at="2026-05-11", timeout=1.0)

    assert [doc.url for doc in bundle.source_documents] == ["https://example.test/hormuz"]
    assert bundle.errors == ["GDELT raw archive found no matches"]
