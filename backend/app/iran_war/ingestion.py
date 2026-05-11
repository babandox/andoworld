from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import hashlib
import json
import os
import csv
import re
import time
from io import StringIO

from backend.app.iran_war.config import load_env_file
from backend.app.iran_war.gdelt_raw import ingest_gdelt_raw_archive
from backend.app.models import MarketMarker, MarketSeriesPoint, PredictionMarketPricePoint, SourceDocument


EVIDENCE_START = "2025-12-01"
DEFAULT_INGEST_TIMEOUT_SECONDS = 15.0
GDELT_PUBLIC_DOC_LOOKBACK_DAYS = 89
GDELT_WINDOW_DAYS = 7
GDELT_MAX_RECORDS_PER_WINDOW = 250
GDELT_REQUEST_PAUSE_SECONDS = 6.0
RELEVANT_WIKIPEDIA_SECTIONS = {
    "background",
    "prelude",
    "rationale",
    "iran nuclear issue",
    "analysis",
    "economic impacts",
    "energy",
    "strait of hormuz",
    "aftermath",
    "reactions",
}
WIKIPEDIA_REFERENCE_LIMIT_PER_PAGE = 250
WIKIPEDIA_SEED_PAGES = [
    "2026 Iran war",
    "Prelude to the 2026 Iran war",
    "Rationale for the 2026 Iran war",
    "Regime change efforts in the 2026 Iran war",
    "Middle Eastern crisis (2023-present)",
]
GDELT_QUERY = '("Iran war" OR "2026 Iran war" OR "Strait of Hormuz" OR "Iran nuclear" OR "US Iran" OR "U.S. Iran" OR "Trump Iran" OR "Truth Social Iran" OR "Iran strike" OR "Iran missile" OR "Iran airspace" OR "Iran ceasefire" OR "Iran Israel" OR "Israel Iran" OR "Iran regime" OR "Tehran")'
POLYMARKET_SEARCHES = ["Iran", "Hormuz", "Iran nuclear", "Iran war", "oil", "crude oil", "WTI", "Hormuz oil"]
POLYMARKET_PUBLIC_SEARCH_LIMIT_PER_TYPE = 50
POLYMARKET_HISTORY_MARKET_LIMIT = 48
FRED_SERIES_IDS = {"Brent": "DCOILBRENTEU", "WTI": "DCOILWTICO", "S&P 500": "SP500"}
IRAN_RELEVANCE_PATTERN = re.compile(r"\b(iran|iranian|tehran|hormuz|irgc|khamenei|israel|israeli|hezbollah|trump|truth social|oil|crude|brent|wti)\b", re.IGNORECASE)
POLYMARKET_NOISE_PATTERN = re.compile(
    r"\b(say|says|mention|mentions)\b|press briefing|hanukkah|wef address|kevin warsh|fed chair|nothing ever happens|send warships through the strait of hormuz",
    re.IGNORECASE,
)


@dataclass
class IngestedSourceBundle:
    source_documents: list[SourceDocument] = field(default_factory=list)
    market_series: list[MarketSeriesPoint] = field(default_factory=list)
    prediction_market_series: list[PredictionMarketPricePoint] = field(default_factory=list)
    market_markers: list[MarketMarker] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_live_data(self) -> bool:
        return bool(self.source_documents or self.market_series or self.prediction_market_series or self.market_markers)


def ingest_live_sources(timeout: float = DEFAULT_INGEST_TIMEOUT_SECONDS) -> IngestedSourceBundle:
    load_env_file()
    retrieved_at = datetime.now(timezone.utc).date().isoformat()
    bundle = IngestedSourceBundle()

    for source_call in (
        lambda: ingest_wikipedia(retrieved_at=retrieved_at, timeout=timeout),
        lambda: ingest_gdelt(retrieved_at=retrieved_at, timeout=timeout),
        lambda: ingest_polymarket(retrieved_at=retrieved_at, timeout=timeout),
        lambda: ingest_fred(retrieved_at=retrieved_at, timeout=timeout),
    ):
        try:
            partial = source_call()
            bundle.source_documents.extend(partial.source_documents)
            bundle.market_series.extend(partial.market_series)
            bundle.prediction_market_series.extend(partial.prediction_market_series)
            bundle.market_markers.extend(partial.market_markers)
            bundle.errors.extend(partial.errors)
        except Exception as exc:
            bundle.errors.append(f"{type(exc).__name__}: {exc}")

    return _dedupe_bundle(bundle)


def ingest_wikipedia(retrieved_at: str, timeout: float = 8.0) -> IngestedSourceBundle:
    try:
        import wikipediaapi
    except ImportError:
        return IngestedSourceBundle(errors=["wikipedia-api package is not installed"])

    wiki = wikipediaapi.Wikipedia(
        user_agent="IranWarCausalTimeline/0.1 (local research app)",
        language="en",
        timeout=timeout,
    )
    docs: list[SourceDocument] = []
    errors: list[str] = []
    for title in WIKIPEDIA_SEED_PAGES:
        try:
            page = wiki.page(title)
            exists = page.exists() if callable(page.exists) else bool(page.exists)
            if not exists:
                errors.append(f"Wikipedia page not found: {title}")
                continue
            revision_id = fetch_wikipedia_revision_id(title, timeout=timeout)
            docs.extend(parse_wikipedia_page(page, retrieved_at=retrieved_at, revision_id=revision_id))
            docs.extend(fetch_wikipedia_reference_documents(title, str(getattr(page, "fullurl", "") or ""), retrieved_at=retrieved_at, timeout=timeout))
        except Exception as exc:
            errors.append(f"Wikipedia {title}: {type(exc).__name__}")
    return IngestedSourceBundle(source_documents=docs, errors=errors)


def parse_wikipedia_page(page: Any, retrieved_at: str, revision_id: str | None = None) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    page_title = str(getattr(page, "title", "Wikipedia page"))
    page_url = getattr(page, "fullurl", None)
    page_id = getattr(page, "pageid", None)

    for section, ancestor_is_relevant in _flatten_sections_with_relevance(getattr(page, "sections", [])):
        section_title = str(getattr(section, "title", ""))
        text = str(getattr(section, "text", "") or "").strip()
        if not text or not (ancestor_is_relevant or _is_relevant_wikipedia_section(section_title)):
            continue
        docs.append(
            SourceDocument(
                id=f"wiki:{_slug(page_title)}:{_slug(section_title)}",
                source_type="wikipedia",
                title=f"{page_title} - {section_title}",
                url=page_url,
                retrieved_at=retrieved_at,
                revision_id=revision_id or (str(page_id) if page_id else None),
                section_title=section_title,
                excerpt=_clip(text),
            )
        )

    if not docs:
        summary = str(getattr(page, "summary", "") or "").strip()
        if summary:
            docs.append(
                SourceDocument(
                    id=f"wiki:{_slug(page_title)}:summary",
                    source_type="wikipedia",
                    title=f"{page_title} - Summary",
                    url=page_url,
                    retrieved_at=retrieved_at,
                    revision_id=revision_id or (str(page_id) if page_id else None),
                    section_title="Summary",
                    excerpt=_clip(summary),
                )
            )
    return docs


def fetch_wikipedia_revision_id(title: str, timeout: float = 8.0) -> str | None:
    params = urlencode(
        {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvprop": "ids|timestamp",
            "format": "json",
            "formatversion": "2",
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    payload = _get_json(url, timeout=timeout)
    try:
        revisions = payload["query"]["pages"][0].get("revisions", [])
        if revisions:
            return str(revisions[0].get("revid"))
    except (KeyError, IndexError, TypeError):
        return None
    return None


def fetch_wikipedia_reference_documents(title: str, page_url: str, retrieved_at: str, timeout: float = 8.0) -> list[SourceDocument]:
    params = urlencode(
        {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "formatversion": "2",
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    payload = _get_json(url, timeout=timeout)
    html = ""
    try:
        text_payload = payload["parse"]["text"]
        html = text_payload if isinstance(text_payload, str) else text_payload.get("*", "")
    except (KeyError, TypeError, AttributeError):
        return []
    return parse_wikipedia_references_html(title, html, retrieved_at=retrieved_at, page_url=page_url)


def parse_wikipedia_references_html(page_title: str, html: str, retrieved_at: str, page_url: str | None = None) -> list[SourceDocument]:
    citations = _WikipediaReferenceParser().parse(html)
    docs: list[SourceDocument] = []
    seen: set[str] = set()
    for citation in citations:
        text = _normalize_reference_text(citation.text)
        if not text:
            continue
        published_at = _reference_published_date(text)
        if not published_at or published_at < EVIDENCE_START:
            continue
        if not _is_relevant_iran_war_text(text):
            continue
        key = _normalized_title(text)
        if key in seen:
            continue
        seen.add(key)
        title = _reference_title(text)
        docs.append(
            SourceDocument(
                id=f"wiki-ref:{_slug(page_title)}:{_stable_id(text)}",
                source_type="wikipedia_reference",
                title=title,
                url=citation.url or page_url,
                published_at=published_at,
                retrieved_at=retrieved_at,
                section_title="References",
                excerpt=_clip(f"{page_title} reference citation: {text}"),
            )
        )
        if len(docs) >= WIKIPEDIA_REFERENCE_LIMIT_PER_PAGE:
            break
    return docs


def ingest_gdelt(retrieved_at: str, timeout: float = 8.0) -> IngestedSourceBundle:
    docs: list[SourceDocument] = []
    errors: list[str] = []
    if os.getenv("GDELT_RAW_ARCHIVE_ENABLED", "1").lower() not in {"0", "false", "no"}:
        raw_result = ingest_gdelt_raw_archive(
            retrieved_at=retrieved_at,
            start=os.getenv("GDELT_RAW_ARCHIVE_START", EVIDENCE_START),
            end=os.getenv("GDELT_RAW_ARCHIVE_END", retrieved_at),
            timeout=timeout,
        )
        errors.extend(raw_result.errors)
        if raw_result.source_documents:
            return IngestedSourceBundle(source_documents=raw_result.source_documents, errors=errors)

    for url in build_gdelt_request_urls(max_records=GDELT_MAX_RECORDS_PER_WINDOW):
        try:
            payload = _get_json(url, timeout=timeout, retries=2, retry_pause_seconds=GDELT_REQUEST_PAUSE_SECONDS)
            docs.extend(parse_gdelt_articles(payload, retrieved_at=retrieved_at, query=GDELT_QUERY))
            time.sleep(GDELT_REQUEST_PAUSE_SECONDS)
        except Exception as exc:
            errors.append(f"GDELT DOC query failed: {_error_label(exc)}")
    return IngestedSourceBundle(source_documents=docs, errors=errors)


def build_gdelt_request_urls(max_records: int = GDELT_MAX_RECORDS_PER_WINDOW, now: str | datetime | None = None) -> list[str]:
    current = _coerce_datetime(now) if now is not None else datetime.now(timezone.utc)
    requested_start = datetime.fromisoformat(EVIDENCE_START).replace(tzinfo=timezone.utc)
    public_doc_start = current - timedelta(days=GDELT_PUBLIC_DOC_LOOKBACK_DAYS)
    effective_start = max(requested_start, public_doc_start)
    windows = _date_windows(effective_start, current, days=GDELT_WINDOW_DAYS)
    records_per_window = max(1, min(250, max_records))

    urls: list[str] = []
    for start, end in windows:
        params = urlencode(
            {
                "query": GDELT_QUERY,
                "mode": "artlist",
                "format": "json",
                "maxrecords": str(records_per_window),
                "sort": "datedesc",
                "startdatetime": _gdelt_datetime(start),
                "enddatetime": _gdelt_datetime(end),
            }
        )
        urls.append(f"https://api.gdeltproject.org/api/v2/doc/doc?{params}")
    return urls


def parse_gdelt_articles(payload: dict[str, Any], retrieved_at: str, query: str) -> list[SourceDocument]:
    articles = payload.get("articles", [])
    docs: list[SourceDocument] = []
    seen_titles: set[str] = set()
    for index, article in enumerate(articles):
        url = article.get("url")
        title = article.get("title") or url or f"GDELT article {index + 1}"
        if not _has_readable_title(title):
            continue
        if not _is_relevant_iran_war_text(title, url, article.get("domain")):
            continue
        title_key = _normalized_title(title)
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        published_at = article.get("seendate") or article.get("date")
        domain = article.get("domain") or ""
        docs.append(
            SourceDocument(
                id=f"gdelt:{_stable_id(url or title)}",
                source_type="gdelt",
                title=str(title),
                url=str(url) if url else None,
                published_at=str(published_at) if published_at else None,
                retrieved_at=retrieved_at,
                excerpt=_clip(f"{domain} article matched query {query}: {title}"),
            )
        )
    return docs


def ingest_polymarket(retrieved_at: str, timeout: float = 8.0) -> IngestedSourceBundle:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for url in build_polymarket_search_urls():
        try:
            payload = _get_json(url, timeout=timeout, retries=1)
            records.extend(extract_polymarket_search_records(payload))
        except Exception as exc:
            errors.append(f"Polymarket search: {_error_label(exc)}")
    records = _dedupe_polymarket_records(records)
    history_records = _select_polymarket_history_records(records, limit=POLYMARKET_HISTORY_MARKET_LIMIT)
    docs = parse_polymarket_markets(history_records, retrieved_at=retrieved_at)
    history_points: list[PredictionMarketPricePoint] = []
    for record in history_records:
        try:
            history_points.extend(fetch_polymarket_price_history(record, timeout=timeout))
        except Exception as exc:
            question = record.get("question") or record.get("title") or record.get("id") or "market"
            errors.append(f"Polymarket history {question}: {_error_label(exc)}")
    return IngestedSourceBundle(source_documents=docs, prediction_market_series=history_points, errors=errors)


def build_polymarket_search_urls() -> list[str]:
    urls: list[str] = []
    for search in POLYMARKET_SEARCHES:
        params = urlencode(
            {
                "q": search,
                "limit_per_type": str(POLYMARKET_PUBLIC_SEARCH_LIMIT_PER_TYPE),
                "keep_closed_markets": "1",
            }
        )
        urls.append(f"https://gamma-api.polymarket.com/public-search?{params}")
    return urls


def parse_polymarket_search_results(payload: Any, retrieved_at: str) -> list[SourceDocument]:
    return parse_polymarket_markets(extract_polymarket_search_records(payload), retrieved_at=retrieved_at)


def extract_polymarket_search_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    records: list[dict[str, Any]] = []
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        markets = event.get("markets") or []
        if markets:
            records.extend(market for market in markets if isinstance(market, dict))
            continue
        records.append(
            {
                "id": event.get("id"),
                "question": event.get("title"),
                "description": event.get("description"),
                "slug": event.get("slug"),
                "closed": event.get("closed"),
                "active": event.get("active"),
                "endDate": event.get("endDate"),
                "createdAt": event.get("creationDate") or event.get("createdAt"),
            }
        )
    for market in payload.get("markets") or []:
        if isinstance(market, dict):
            records.append(market)
    return records


def parse_polymarket_markets(payload: Any, retrieved_at: str) -> list[SourceDocument]:
    records = payload.get("markets", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return []

    docs: list[SourceDocument] = []
    for record in records:
        question = record.get("question") or record.get("title")
        market_id = str(record.get("id") or record.get("conditionId") or _stable_id(str(question)))
        if not question:
            continue
        if not _is_relevant_iran_war_text(question, record.get("description"), record.get("slug")):
            continue
        if not _is_polymarket_scenario_record(record):
            continue
        if not _polymarket_record_overlaps_evidence_window(record):
            continue
        closed = bool(record.get("closed"))
        outcomes = _jsonish_list(record.get("outcomes"))
        prices = _jsonish_list(record.get("outcomePrices"))
        probability_bits: list[str] = []
        for outcome, price in zip(outcomes, prices):
            try:
                probability_bits.append(f"{outcome}: {float(price) * 100:.1f}%")
            except (TypeError, ValueError):
                continue
        status = "closed" if closed else "active"
        url = record.get("url") or (f"https://polymarket.com/event/{record.get('slug')}" if record.get("slug") else "https://polymarket.com/")
        docs.append(
            SourceDocument(
                id=f"polymarket:{market_id}",
                source_type="polymarket",
                title=str(question),
                url=str(url) if url else None,
                published_at=record.get("endDate") or record.get("createdAt"),
                retrieved_at=retrieved_at,
                excerpt=_clip(f"{status} market. " + (", ".join(probability_bits) if probability_bits else "No outcome prices available.")),
            )
        )
    return docs


def fetch_polymarket_price_history(record: dict[str, Any], timeout: float = 8.0) -> list[PredictionMarketPricePoint]:
    selection = _select_polymarket_token(record)
    if selection is None:
        return []
    token_id, outcome = selection
    start = _record_datetime(record, "startDate", "createdAt", "creationDate")
    end = _record_datetime(record, "closedTime", "endDate", "umaEndDate", "updatedAt") or datetime.now(timezone.utc)
    if start is None:
        start = datetime.fromisoformat(EVIDENCE_START).replace(tzinfo=timezone.utc)
    if end <= start:
        end = datetime.now(timezone.utc)
    params = urlencode(
        {
            "market": token_id,
            "startTs": str(int(start.timestamp())),
            "endTs": str(int(end.timestamp())),
            "interval": "1d",
            "fidelity": "1440",
        }
    )
    try:
        payload = _get_json(f"https://clob.polymarket.com/prices-history?{params}", timeout=timeout, retries=1)
    except HTTPError as exc:
        if exc.code == 400:
            point = polymarket_current_price_point(record, token_id=token_id, outcome=outcome)
            return [point] if point else []
        raise
    points = parse_polymarket_price_history(payload, record=record, token_id=token_id, outcome=outcome)
    if points:
        return points
    point = polymarket_current_price_point(record, token_id=token_id, outcome=outcome)
    return [point] if point else []


def polymarket_current_price_point(record: dict[str, Any], *, token_id: str, outcome: str) -> PredictionMarketPricePoint | None:
    fallback = _current_polymarket_probability(record, outcome)
    if fallback is None:
        return None
    date = (
        _record_datetime(record, "updatedAt", "closedTime", "endDate")
        or datetime.now(timezone.utc)
    ).date().isoformat()
    return PredictionMarketPricePoint(
        market_id=_polymarket_market_id(record),
        question=str(record.get("question") or record.get("title")),
        token_id=token_id,
        outcome=outcome,
        date=date,
        probability=fallback,
        status=_polymarket_status(record),
        market_start=_date_prefix(record.get("startDate") or record.get("createdAt") or record.get("creationDate")),
        market_end=_date_prefix(record.get("closedTime") or record.get("endDate") or record.get("umaEndDate")),
        url=_polymarket_url(record),
    )


def parse_polymarket_price_history(
    payload: Any,
    *,
    record: dict[str, Any],
    token_id: str,
    outcome: str,
) -> list[PredictionMarketPricePoint]:
    history = payload.get("history", []) if isinstance(payload, dict) else []
    if not isinstance(history, list):
        return []
    daily: dict[str, tuple[int, float]] = {}
    for item in history:
        if not isinstance(item, dict):
            continue
        try:
            timestamp = int(float(item.get("t")))
            probability = _normalize_probability(float(item.get("p")))
        except (TypeError, ValueError):
            continue
        date = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        if date not in daily or timestamp >= daily[date][0]:
            daily[date] = (timestamp, probability)

    question = str(record.get("question") or record.get("title") or "Polymarket market")
    market_id = _polymarket_market_id(record)
    status = _polymarket_status(record)
    market_start = _date_prefix(record.get("startDate") or record.get("createdAt") or record.get("creationDate"))
    market_end = _date_prefix(record.get("closedTime") or record.get("endDate") or record.get("umaEndDate"))
    url = _polymarket_url(record)
    return [
        PredictionMarketPricePoint(
            market_id=market_id,
            question=question,
            token_id=token_id,
            outcome=outcome,
            date=date,
            probability=probability,
            status=status,
            market_start=market_start,
            market_end=market_end,
            url=url,
        )
        for date, (_, probability) in sorted(daily.items())
    ]


def _dedupe_polymarket_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for record in records:
        question = record.get("question") or record.get("title")
        if not question:
            continue
        key = _polymarket_market_id(record)
        if key not in deduped:
            deduped[key] = record
            continue
        existing = deduped[key]
        record_date = _date_prefix(record.get("updatedAt") or record.get("closedTime") or record.get("endDate")) or ""
        existing_date = _date_prefix(existing.get("updatedAt") or existing.get("closedTime") or existing.get("endDate")) or ""
        if record_date > existing_date:
            deduped[key] = record
    return list(deduped.values())


def _select_polymarket_history_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for record in records:
        question = record.get("question") or record.get("title")
        if not question:
            continue
        if not _is_relevant_iran_war_text(question, record.get("description"), record.get("slug")):
            continue
        if not _is_polymarket_scenario_record(record):
            continue
        if not _polymarket_record_overlaps_evidence_window(record):
            continue
        if _select_polymarket_token(record) is None:
            continue
        candidates.append(record)
    resolved = [record for record in candidates if bool(record.get("closed"))]
    active = [record for record in candidates if not bool(record.get("closed"))]
    resolved_limit = min(len(resolved), max(1, int(limit * 0.7))) if resolved else 0
    active_limit = max(0, limit - resolved_limit)
    selected = _pick_polymarket_records_by_month(resolved, resolved_limit)
    selected.extend(_sort_polymarket_records(active)[:active_limit])

    selected_ids = {_polymarket_market_id(record) for record in selected}
    if len(selected) < limit:
        for record in _sort_polymarket_records(candidates):
            if _polymarket_market_id(record) in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(_polymarket_market_id(record))
            if len(selected) >= limit:
                break
    return selected[:limit]


def _pick_polymarket_records_by_month(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in _sort_polymarket_records(records):
        month = (_polymarket_reference_date(record) or "9999-99-99")[:7]
        groups.setdefault(month, []).append(record)
    months = sorted(groups)
    selected: list[dict[str, Any]] = []
    while len(selected) < limit and any(groups.values()):
        for month in months:
            if not groups[month]:
                continue
            selected.append(groups[month].pop(0))
            if len(selected) >= limit:
                break
    return selected


def _sort_polymarket_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            _polymarket_relevance_score(record),
            _polymarket_reference_date(record) or "",
        ),
        reverse=True,
    )


def _polymarket_reference_date(record: dict[str, Any]) -> str | None:
    return _date_prefix(
        record.get("closedTime")
        or record.get("endDate")
        or record.get("startDate")
        or record.get("createdAt")
        or record.get("creationDate")
        or record.get("updatedAt")
    )


def _polymarket_relevance_score(record: dict[str, Any]) -> int:
    text = " ".join(str(record.get(field) or "") for field in ("question", "title", "description", "slug")).casefold()
    score = 0
    for pattern, value in (
        (r"\bpeace deal|ceasefire|nuclear deal|nuclear talks\b", 18),
        (r"\bclose the strait|strait of hormuz|airspace|blockade|unrestricted shipping\b", 16),
        (r"\btarget.*nuclear|nuclear facility|target tehran|declare war\b", 14),
        (r"\biran|iranian|tehran\b", 12),
        (r"\bhormuz|strait\b", 10),
        (r"\bnuclear|jcpoa|khamenei|irgc|regime\b", 8),
        (r"\bwar|strike|ceasefire|peace|trump\b", 6),
        (r"\boil|crude|brent|wti\b", 4),
    ):
        if re.search(pattern, text):
            score += value
    return score


def _is_polymarket_scenario_record(record: dict[str, Any]) -> bool:
    text = " ".join(str(record.get(field) or "") for field in ("question", "title", "description", "slug"))
    return not POLYMARKET_NOISE_PATTERN.search(text)


def _polymarket_record_overlaps_evidence_window(record: dict[str, Any]) -> bool:
    dates = [
        _date_prefix(record.get(field))
        for field in ("createdAt", "creationDate", "startDate", "endDate", "closedTime", "umaEndDate")
    ]
    normalized_dates = [date for date in dates if date]
    if not normalized_dates:
        return True
    return max(normalized_dates) >= EVIDENCE_START


def _select_polymarket_token(record: dict[str, Any]) -> tuple[str, str] | None:
    token_ids = [str(token_id) for token_id in _jsonish_list(record.get("clobTokenIds")) if str(token_id)]
    outcomes = [str(outcome) for outcome in _jsonish_list(record.get("outcomes"))]
    if not token_ids:
        return None
    index = next((position for position, outcome in enumerate(outcomes) if outcome.casefold() == "yes"), 0)
    if index >= len(token_ids):
        index = 0
    outcome = outcomes[index] if index < len(outcomes) else "Yes"
    return token_ids[index], outcome


def _current_polymarket_probability(record: dict[str, Any], selected_outcome: str) -> float | None:
    outcomes = [str(outcome) for outcome in _jsonish_list(record.get("outcomes"))]
    prices = _jsonish_list(record.get("outcomePrices"))
    index = next((position for position, outcome in enumerate(outcomes) if outcome == selected_outcome), 0)
    if index >= len(prices):
        return None
    try:
        return _normalize_probability(float(prices[index]))
    except (TypeError, ValueError):
        return None


def _polymarket_market_id(record: dict[str, Any]) -> str:
    question = record.get("question") or record.get("title") or ""
    return str(record.get("id") or record.get("conditionId") or _stable_id(str(question)))


def _polymarket_url(record: dict[str, Any]) -> str | None:
    url = record.get("url")
    if url:
        return str(url)
    if record.get("slug"):
        return f"https://polymarket.com/event/{record.get('slug')}"
    return "https://polymarket.com/"


def _polymarket_status(record: dict[str, Any]) -> str:
    if bool(record.get("closed")):
        return "resolved"
    if record.get("active") is False:
        return "closed"
    return "active"


def _normalize_probability(value: float) -> float:
    probability = value / 100 if value > 1 else value
    return max(0.0, min(1.0, probability))


def _record_datetime(record: dict[str, Any], *fields: str) -> datetime | None:
    for field in fields:
        value = record.get(field)
        if not value:
            continue
        parsed = _parse_datetime(value)
        if parsed:
            return parsed
    return None


def ingest_fred(retrieved_at: str | None = None, timeout: float = 8.0) -> IngestedSourceBundle:
    load_env_file()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return IngestedSourceBundle(errors=["FRED_API_KEY is not configured"])

    series_map = {series_id: series_name for series_name, series_id in FRED_SERIES_IDS.items()}
    points: list[MarketSeriesPoint] = []
    errors: list[str] = []
    for series_id, series_name in series_map.items():
        params = urlencode(
            {
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": EVIDENCE_START,
            }
        )
        url = f"https://api.stlouisfed.org/fred/series/observations?{params}"
        try:
            payload = _get_json(url, timeout=timeout)
            points.extend(parse_fred_observations(payload, series=series_name))
        except Exception as exc:
            try:
                points.extend(fetch_fred_csv_series(series_id=series_id, series=series_name, timeout=timeout))
            except Exception:
                errors.append(f"FRED {series_id}: {type(exc).__name__}")
    docs = build_fred_source_documents(
        points,
        retrieved_at=retrieved_at or datetime.now(timezone.utc).date().isoformat(),
    )
    return IngestedSourceBundle(source_documents=docs, market_series=points, errors=errors)


def parse_fred_observations(payload: dict[str, Any], series: str) -> list[MarketSeriesPoint]:
    points: list[MarketSeriesPoint] = []
    for observation in payload.get("observations", []):
        value = observation.get("value")
        if value in {None, "."}:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        points.append(
            MarketSeriesPoint(
                series=series,  # type: ignore[arg-type]
                date=str(observation.get("date")),
                value=numeric,
                source="FRED",
            )
        )
    return points


def build_fred_source_documents(points: list[MarketSeriesPoint], retrieved_at: str) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for series in sorted({point.series for point in points}):
        series_points = [point for point in points if point.series == series]
        if not series_points:
            continue
        dates = sorted(point.date for point in series_points)
        series_id = FRED_SERIES_IDS.get(series, _slug(series))
        docs.append(
            SourceDocument(
                id=f"fred:{_slug(series)}",
                source_type="fred",
                title=f"FRED {series} daily series",
                url=f"https://fred.stlouisfed.org/series/{series_id}",
                published_at=dates[-1],
                retrieved_at=retrieved_at,
                section_title=series,
                excerpt=f"{len(series_points)} observations for {series} from {dates[0]} through {dates[-1]}.",
            )
        )
    return docs


def fetch_fred_csv_series(series_id: str, series: str, timeout: float = 8.0) -> list[MarketSeriesPoint]:
    params = urlencode({"id": series_id, "observation_start": EVIDENCE_START})
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?{params}"
    request = Request(url, headers={"User-Agent": "IranWarCausalTimeline/0.1 local research app"})
    with urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8")
    rows = csv.DictReader(StringIO(text))
    points: list[MarketSeriesPoint] = []
    for row in rows:
        date = row.get("observation_date") or row.get("DATE") or row.get("date")
        value = row.get(series_id)
        if not date or value in {None, "."}:
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue
        if date < EVIDENCE_START:
            continue
        points.append(MarketSeriesPoint(series=series, date=date, value=numeric, source="FRED"))  # type: ignore[arg-type]
    return points


@dataclass
class WikipediaCitation:
    text: str
    url: str | None = None


class _WikipediaReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_reference = False
        self._depth = 0
        self._parts: list[str] = []
        self._url: str | None = None
        self._skip_depth = 0
        self.citations: list[WikipediaCitation] = []

    def parse(self, html: str) -> list[WikipediaCitation]:
        self.feed(html)
        return self.citations

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())
        starts_reference = tag == "li" and attr_map.get("id", "").startswith("cite_note")
        starts_reference = starts_reference or (tag == "span" and "reference-text" in classes)
        if starts_reference and not self._in_reference:
            self._in_reference = True
            self._depth = 1
            self._parts = []
            self._url = None
            return
        if self._in_reference:
            self._depth += 1
            if tag in {"style", "script"}:
                self._skip_depth += 1
            href = attr_map.get("href")
            if tag == "a" and href and href.startswith("http") and not self._url:
                self._url = href

    def handle_endtag(self, tag: str) -> None:
        if not self._in_reference:
            return
        if self._skip_depth and tag in {"style", "script"}:
            self._skip_depth -= 1
        self._depth -= 1
        if self._depth <= 0:
            text = _normalize_reference_text(" ".join(self._parts))
            if text:
                self.citations.append(WikipediaCitation(text=text, url=self._url))
            self._in_reference = False

    def handle_data(self, data: str) -> None:
        if self._in_reference and not self._skip_depth:
            self._parts.append(data)


def _normalize_reference_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"^\}\.mw-parser-output\b.*?(?=[\"“A-Z0-9])", "", text).strip()


def _reference_title(text: str) -> str:
    if match := re.search(r'"([^"]{8,220})"', text):
        return match.group(1).strip()
    if match := re.search(r"“([^”]{8,220})”", text):
        return match.group(1).strip()
    without_leading_authors = re.sub(r"^[A-Z][^()]{1,160}\(\d{1,2}\s+[A-Z][a-z]+\s+\d{4}\)\.\s*", "", text)
    return _clip(without_leading_authors.split(". ")[0].strip(" ."), limit=180)


def _reference_published_date(text: str) -> str | None:
    before_retrieved = re.split(r"\bRetrieved\b", text, maxsplit=1)[0]
    dates: list[str] = []
    for match in re.finditer(r"\b(\d{1,2})\s+([A-Z][a-z]+)\s+((?:19|20)\d{2})\b", before_retrieved):
        day, month, year = match.groups()
        month_number = _month_number(month)
        if month_number:
            dates.append(f"{year}-{month_number}-{int(day):02d}")
    for match in re.finditer(r"\b([A-Z][a-z]+)\s+(\d{1,2}),\s*((?:19|20)\d{2})\b", before_retrieved):
        month, day, year = match.groups()
        month_number = _month_number(month)
        if month_number:
            dates.append(f"{year}-{month_number}-{int(day):02d}")
    return dates[-1] if dates else None


def _month_number(month: str) -> str | None:
    months = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }
    return months.get(month.casefold())


def _dedupe_bundle(bundle: IngestedSourceBundle) -> IngestedSourceBundle:
    docs: dict[str, SourceDocument] = {}
    for doc in bundle.source_documents:
        key = f"gdelt:{_normalized_title(doc.title)}" if doc.source_type == "gdelt" else doc.id
        if key not in docs:
            docs[key] = doc
    points = {(point.series, point.date): point for point in bundle.market_series}
    prediction_points = {
        (point.market_id, point.token_id, point.date): point
        for point in bundle.prediction_market_series
    }
    markers = {marker.id: marker for marker in bundle.market_markers}
    return IngestedSourceBundle(
        source_documents=list(docs.values()),
        market_series=sorted(points.values(), key=lambda point: (point.series, point.date)),
        prediction_market_series=sorted(
            prediction_points.values(),
            key=lambda point: (point.question, point.date),
        ),
        market_markers=list(markers.values()),
        errors=bundle.errors,
    )


def _get_json(url: str, timeout: float, retries: int = 0, retry_pause_seconds: float = 1.5) -> Any:
    request = Request(url, headers={"User-Agent": "IranWarCausalTimeline/0.1 local research app"})
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(retry_pause_seconds * (attempt + 1))
                continue
            raise
        except URLError:
            if attempt < retries:
                time.sleep(retry_pause_seconds * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable JSON fetch retry state")


def _is_relevant_iran_war_text(*values: Any) -> bool:
    text = " ".join(str(value or "") for value in values)
    return bool(IRAN_RELEVANCE_PATTERN.search(text))


def _has_readable_title(value: Any) -> bool:
    normalized = re.sub(r"[^A-Za-z0-9]+", "", str(value or ""))
    return len(normalized) >= 8


def _record_is_recent_enough(record: dict[str, Any]) -> bool:
    dates = [
        _date_prefix(record.get(field))
        for field in ("createdAt", "creationDate", "startDate", "endDate", "closedTime", "umaEndDate", "updatedAt")
    ]
    normalized_dates = [date for date in dates if date]
    if not normalized_dates:
        return True
    return max(normalized_dates) >= EVIDENCE_START


def _date_windows(start: datetime, end: datetime, days: int) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        window_end = min(cursor + timedelta(days=days), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(seconds=1)
    return windows or [(start, end)]


def _coerce_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if re.fullmatch(r"\d{8}", text):
            return datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc)
        if re.fullmatch(r"\d{14}", text):
            return datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _gdelt_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


def _date_prefix(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if len(text) >= 10:
        return text[:10]
    return None


def _error_label(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, URLError):
        return type(exc.reason).__name__ if getattr(exc, "reason", None) else "URL error"
    return type(exc).__name__


def _flatten_sections(sections: list[Any]) -> list[Any]:
    flattened: list[Any] = []
    for section in sections:
        flattened.append(section)
        flattened.extend(_flatten_sections(getattr(section, "sections", []) or []))
    return flattened


def _flatten_sections_with_relevance(sections: list[Any], ancestor_is_relevant: bool = False) -> list[tuple[Any, bool]]:
    flattened: list[tuple[Any, bool]] = []
    for section in sections:
        title = str(getattr(section, "title", ""))
        current_is_relevant = _is_relevant_wikipedia_section(title)
        flattened.append((section, ancestor_is_relevant))
        flattened.extend(_flatten_sections_with_relevance(getattr(section, "sections", []) or [], ancestor_is_relevant or current_is_relevant))
    return flattened


def _is_relevant_wikipedia_section(title: str) -> bool:
    normalized = title.strip().casefold()
    return any(label in normalized for label in RELEVANT_WIKIPEDIA_SECTIONS)


def _jsonish_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _slug(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _normalized_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _clip(value: str, limit: int = 700) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."
