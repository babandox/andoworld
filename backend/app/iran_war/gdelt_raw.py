from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Iterable
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
import csv
import hashlib
import os
import re
import zipfile

from backend.app.models import SourceDocument


MASTERFILELIST_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
DEFAULT_RAW_ARCHIVE_MAX_PAIRS = 12
RAW_ARCHIVE_RELEVANCE_THRESHOLD = 18
RAW_ARCHIVE_DOC_LIMIT = 300
RAW_ARCHIVE_EVENT_LIMIT_PER_FILE = 500

IRAN_TERMS = re.compile(r"\b(iran|iranian|tehran|irgc|khamenei)\b", re.IGNORECASE)
COUNTERPART_TERMS = re.compile(r"\b(israel|israeli|united states|u\.s\.|usa|trump|hormuz|hezbollah|gulf)\b", re.IGNORECASE)
TOPIC_TERMS = re.compile(
    r"\b(hormuz|nuclear|missile|strike|strikes|attack|attacks|ceasefire|peace|sanction|airspace|shipping|warship|regime|threat|warns|warning|drone|oil|tanker|bomb|bunker)\b",
    re.IGNORECASE,
)
DIRECT_CONFLICT_TERMS = re.compile(
    r"\b(strike|strikes|attack|attacks|missile|drone|bomb|bombing|bunker|killed|airstrike|retaliat|tanker)\b",
    re.IGNORECASE,
)
DIPLOMACY_TERMS = re.compile(
    r"\b(talks|ceasefire|peace|deal|negotiat|proposal|mediate|diplomat|iaea|jcpoa|agreement)\b",
    re.IGNORECASE,
)
ECONOMIC_PRESSURE_TERMS = re.compile(
    r"\b(sanction|tariff|economy|economic|currency|inflation|exports?|revenue|banking|maximum pressure)\b",
    re.IGNORECASE,
)
ENERGY_MARKET_TERMS = re.compile(
    r"\b(hormuz|oil|crude|brent|wti|tanker|shipping|energy|gas|lng|freight|insurance)\b",
    re.IGNORECASE,
)
MILITARY_POSTURE_TERMS = re.compile(
    r"\b(warship|airspace|deployment|deploy|troops?|military|base|carrier|defense|missile defense|exercise|mobiliz)\b",
    re.IGNORECASE,
)
REGIONAL_PROXY_TERMS = re.compile(
    r"\b(hezbollah|houthi|houthis|hamas|militia|proxy|syria|syrian|iraq|iraqi|lebanon|lebanese|yemen|yemeni)\b",
    re.IGNORECASE,
)
DOMESTIC_STABILITY_TERMS = re.compile(
    r"\b(protest|unrest|regime|khamenei|supreme leader|opposition|election|dissent|revolt|crackdown)\b",
    re.IGNORECASE,
)
US_POLITICAL_TERMS = re.compile(
    r"\b(trump|congress|white house|pentagon|rubio|vance|leavitt|truth social|administration|republican|democrat)\b",
    re.IGNORECASE,
)
RHETORIC_TERMS = re.compile(r"\b(threat|threaten|warns?|warning|ultimatum|statement|vows?|pledges?)\b", re.IGNORECASE)
BACKGROUND_CONTEXT_TERMS = re.compile(r"\b(background|explainer|history|timeline|analysis|what to know|why it matters)\b", re.IGNORECASE)
RELEVANT_EVENT_ROOTS = {"03", "04", "05", "06", "07", "13", "14", "15", "16", "17", "18", "19", "20"}
CONFLICT_EVENT_ROOTS = {"13", "14", "15", "16", "17", "18", "19", "20"}
DIRECT_CONFLICT_EVENT_ROOTS = {"18", "19", "20"}
COUNTERPART_COUNTRY_CODES = {"ISR", "USA", "US", "SYR", "LBN", "JOR", "IRQ", "SAU", "ARE", "QAT", "BHR", "KWT", "OMN"}


@dataclass(frozen=True)
class GdeltArchiveFile:
    timestamp: str
    file_type: str
    url: str
    size: int
    md5: str


@dataclass(frozen=True)
class RawGdeltEvent:
    event_id: str
    sql_date: str
    date_added: str
    actor1_name: str
    actor1_country_code: str
    actor2_name: str
    actor2_country_code: str
    event_code: str
    event_root_code: str
    quad_class: str
    goldstein_scale: str
    avg_tone: str
    source_url: str
    signal_family: str
    signal_strength: int
    forecast_direction: str
    relevance_score: int


@dataclass(frozen=True)
class GdeltSignalClassification:
    signal_family: str
    signal_strength: int
    forecast_direction: str
    relevance_score: int


@dataclass(frozen=True)
class RawGdeltMention:
    event_id: str
    mention_time: str
    source_name: str
    url: str
    confidence: str
    tone: str


@dataclass
class RawGdeltArchiveResult:
    source_documents: list[SourceDocument] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_gdelt_masterfilelist(
    text: str,
    *,
    start: str,
    end: str,
    file_types: set[str] | None = None,
) -> list[GdeltArchiveFile]:
    accepted_types = file_types or {"export", "mentions"}
    files: list[GdeltArchiveFile] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) != 3:
            continue
        size_text, md5, url = parts
        match = re.search(r"/(?P<timestamp>\d{14})\.(?P<kind>export|mentions)\.CSV\.zip$", url, re.IGNORECASE)
        if not match:
            continue
        timestamp = match.group("timestamp")
        file_type = match.group("kind").casefold()
        if file_type not in accepted_types:
            continue
        day = _timestamp_to_date(timestamp)
        if start <= day <= end:
            files.append(
                GdeltArchiveFile(
                    timestamp=timestamp,
                    file_type=file_type,
                    url=url,
                    size=int(size_text),
                    md5=md5,
                )
            )
    return sorted(files, key=lambda item: (item.timestamp, item.file_type))


def parse_gdelt_export_rows(text: str, *, limit: int = RAW_ARCHIVE_EVENT_LIMIT_PER_FILE) -> list[RawGdeltEvent]:
    events: list[RawGdeltEvent] = []
    reader = csv.reader(StringIO(text), delimiter="\t")
    for columns in reader:
        if len(columns) < 61:
            continue
        classification = _classify_gdelt_signal(columns)
        if classification is None or classification.relevance_score < RAW_ARCHIVE_RELEVANCE_THRESHOLD:
            continue
        events.append(_event_from_columns(columns, classification=classification))
        if len(events) >= limit:
            break
    return events


def parse_gdelt_mentions_rows(text: str, *, event_ids: set[str]) -> dict[str, list[RawGdeltMention]]:
    mentions: dict[str, list[RawGdeltMention]] = {}
    seen: set[tuple[str, str]] = set()
    reader = csv.reader(StringIO(text), delimiter="\t")
    for columns in reader:
        if len(columns) < 6:
            continue
        event_id = columns[0]
        if event_id not in event_ids:
            continue
        url = columns[5]
        if not url:
            continue
        key = (event_id, _normalized_url(url))
        if key in seen:
            continue
        seen.add(key)
        mentions.setdefault(event_id, []).append(
            RawGdeltMention(
                event_id=event_id,
                mention_time=columns[2] if len(columns) > 2 else "",
                source_name=columns[4] if len(columns) > 4 else "",
                url=url,
                confidence=columns[11] if len(columns) > 11 else "",
                tone=columns[13] if len(columns) > 13 else "",
            )
        )
    return mentions


def build_gdelt_source_documents(
    events: list[RawGdeltEvent],
    mentions: dict[str, list[RawGdeltMention]],
    *,
    retrieved_at: str,
    limit: int = RAW_ARCHIVE_DOC_LIMIT,
) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for event in sorted(events, key=lambda item: (item.date_added or item.sql_date, item.event_id)):
        event_mentions = mentions.get(event.event_id) or [
            RawGdeltMention(
                event_id=event.event_id,
                mention_time=event.date_added,
                source_name=_domain(event.source_url),
                url=event.source_url,
                confidence="",
                tone=event.avg_tone,
            )
        ]
        for mention in event_mentions:
            url = mention.url or event.source_url
            normalized_url = _normalized_url(url)
            if normalized_url in seen_urls:
                continue
            title = _title_from_url(url) or f"GDELT Event {event.event_code}: {event.actor1_name} / {event.actor2_name}"
            normalized_title = _normalized_title(title)
            if normalized_title in seen_titles:
                continue
            seen_urls.add(normalized_url)
            seen_titles.add(normalized_title)
            docs.append(
                SourceDocument(
                    id=f"gdelt:{_stable_id(normalized_url or url or event.event_id)}",
                    source_type="gdelt",
                    title=title,
                    url=url or None,
                    published_at=mention.mention_time or event.date_added or event.sql_date,
                    retrieved_at=retrieved_at,
                    section_title="GDELT raw archive",
                    excerpt=_clip(
                        "Raw GDELT archive match. "
                        f"EventID {event.event_id}; EventCode {event.event_code}; Root {event.event_root_code}; "
                        f"SignalFamily {event.signal_family}; SignalStrength {event.signal_strength}; "
                        f"ForecastDirection {event.forecast_direction}; "
                        f"QuadClass {event.quad_class}; Actor1 {event.actor1_name or event.actor1_country_code}; "
                        f"Actor2 {event.actor2_name or event.actor2_country_code}; Goldstein {event.goldstein_scale}; "
                        f"AvgTone {event.avg_tone}; MentionSource {mention.source_name}; RelevanceScore {event.relevance_score}."
                    ),
                )
            )
            if len(docs) >= limit:
                return docs
    return docs


def ingest_gdelt_raw_archive(
    *,
    retrieved_at: str,
    start: str,
    end: str,
    timeout: float = 8.0,
    max_pairs: int | None = None,
) -> RawGdeltArchiveResult:
    pair_limit = max_pairs if max_pairs is not None else _env_int("GDELT_RAW_ARCHIVE_MAX_PAIRS", DEFAULT_RAW_ARCHIVE_MAX_PAIRS)
    try:
        manifest_text = _fetch_text(MASTERFILELIST_URL, timeout=timeout)
    except Exception as exc:
        return RawGdeltArchiveResult(errors=[f"GDELT raw archive manifest failed: {type(exc).__name__}"])

    files = parse_gdelt_masterfilelist(manifest_text, start=start, end=end, file_types={"export", "mentions"})
    pairs = _select_file_pairs(files, max_pairs=pair_limit)
    if not pairs:
        return RawGdeltArchiveResult(errors=["GDELT raw archive found no export/mentions file pairs in the evidence window."])

    docs: list[SourceDocument] = []
    errors: list[str] = []
    for export_file, mentions_file in pairs:
        try:
            export_text = _fetch_zip_text(export_file.url, timeout=timeout)
            events = parse_gdelt_export_rows(export_text)
            if not events:
                continue
            mentions_text = _fetch_zip_text(mentions_file.url, timeout=timeout)
            mentions = parse_gdelt_mentions_rows(mentions_text, event_ids={event.event_id for event in events})
            docs.extend(build_gdelt_source_documents(events, mentions, retrieved_at=retrieved_at))
        except Exception as exc:
            errors.append(f"GDELT raw archive {export_file.timestamp}: {type(exc).__name__}")
    return RawGdeltArchiveResult(source_documents=_dedupe_documents(docs), errors=errors)


def _event_from_columns(columns: list[str], *, classification: GdeltSignalClassification) -> RawGdeltEvent:
    return RawGdeltEvent(
        event_id=columns[0],
        sql_date=columns[1],
        actor1_name=columns[6],
        actor1_country_code=columns[7],
        actor2_name=columns[16],
        actor2_country_code=columns[17],
        event_code=columns[26],
        event_root_code=columns[28],
        quad_class=columns[29],
        goldstein_scale=columns[30],
        avg_tone=columns[34],
        date_added=columns[59],
        source_url=columns[60],
        signal_family=classification.signal_family,
        signal_strength=classification.signal_strength,
        forecast_direction=classification.forecast_direction,
        relevance_score=classification.relevance_score,
    )


def _gdelt_relevance_score(columns: list[str]) -> int:
    classification = _classify_gdelt_signal(columns)
    return classification.relevance_score if classification else 0


def _classify_gdelt_signal(columns: list[str]) -> GdeltSignalClassification | None:
    actor_text = _column_text(columns, 5, 6, 7, 15, 16, 17)
    url_text = _url_signal_text(columns[60])
    primary_text = f"{actor_text} {url_text}".strip()
    actor_country_codes = {columns[index].upper() for index in (7, 17) if index < len(columns) and columns[index]}
    event_root = columns[28]
    quad_class = columns[29]

    actor_has_iran = "IRN" in actor_country_codes or bool(IRAN_TERMS.search(actor_text))
    url_has_iran = bool(IRAN_TERMS.search(url_text))
    has_iran = actor_has_iran or url_has_iran
    if not has_iran:
        return None

    has_counterpart = bool(actor_country_codes.intersection(COUNTERPART_COUNTRY_CODES) or COUNTERPART_TERMS.search(primary_text))
    has_relevant_event_pair = actor_has_iran and (
        event_root in DIRECT_CONFLICT_EVENT_ROOTS or (event_root in RELEVANT_EVENT_ROOTS and has_counterpart)
    )
    if not (url_has_iran or has_relevant_event_pair):
        return None

    family = _signal_family(primary_text, event_root=event_root, quad_class=quad_class)
    direction = _forecast_direction(family, primary_text)
    strength = _signal_strength(family, event_root=event_root, quad_class=quad_class, text=primary_text)

    score = 10 + strength * 4
    if url_has_iran:
        score += 4
    if has_counterpart:
        score += 5
    if event_root in RELEVANT_EVENT_ROOTS:
        score += 3
    if event_root in CONFLICT_EVENT_ROOTS:
        score += 3
    if TOPIC_TERMS.search(primary_text):
        score += 4
    return GdeltSignalClassification(
        signal_family=family,
        signal_strength=strength,
        forecast_direction=direction,
        relevance_score=score,
    )


def _signal_family(text: str, *, event_root: str, quad_class: str) -> str:
    if event_root in DIRECT_CONFLICT_EVENT_ROOTS or quad_class == "4" or DIRECT_CONFLICT_TERMS.search(text):
        return "direct_conflict_signal"
    if DIPLOMACY_TERMS.search(text):
        return "diplomacy_signal"
    if ECONOMIC_PRESSURE_TERMS.search(text):
        return "economic_pressure_signal"
    if ENERGY_MARKET_TERMS.search(text):
        return "energy_market_signal"
    if MILITARY_POSTURE_TERMS.search(text):
        return "military_posture_signal"
    if REGIONAL_PROXY_TERMS.search(text):
        return "regional_proxy_signal"
    if event_root == "01" and BACKGROUND_CONTEXT_TERMS.search(text):
        return "background_context"
    if DOMESTIC_STABILITY_TERMS.search(text):
        return "domestic_stability_signal"
    if RHETORIC_TERMS.search(text) or event_root in {"13", "14", "15", "16", "17"}:
        return "rhetoric_signal"
    if US_POLITICAL_TERMS.search(text):
        return "us_political_signal"
    return "background_context"


def _forecast_direction(family: str, text: str) -> str:
    if family == "diplomacy_signal":
        if re.search(r"\b(fail|failed|collapse|collapsed|reject|rejected|stall|stalled)\b", text, re.IGNORECASE):
            return "escalatory"
        return "deescalatory"
    if family == "background_context":
        return "background"
    if family == "us_political_signal":
        return "uncertain"
    if family in {
        "direct_conflict_signal",
        "military_posture_signal",
        "economic_pressure_signal",
        "energy_market_signal",
        "domestic_stability_signal",
        "regional_proxy_signal",
        "rhetoric_signal",
    }:
        return "escalatory"
    return "uncertain"


def _signal_strength(family: str, *, event_root: str, quad_class: str, text: str) -> int:
    strength_by_family = {
        "direct_conflict_signal": 4,
        "military_posture_signal": 3,
        "economic_pressure_signal": 3,
        "energy_market_signal": 3,
        "regional_proxy_signal": 3,
        "diplomacy_signal": 2,
        "domestic_stability_signal": 2,
        "rhetoric_signal": 2,
        "us_political_signal": 2,
        "background_context": 1,
    }
    strength = strength_by_family.get(family, 1)
    if event_root in DIRECT_CONFLICT_EVENT_ROOTS or quad_class == "4":
        strength += 1
    if len({term for term in (DIRECT_CONFLICT_TERMS, DIPLOMACY_TERMS, ECONOMIC_PRESSURE_TERMS, ENERGY_MARKET_TERMS) if term.search(text)}) >= 2:
        strength += 1
    return min(strength, 5)


def _column_text(columns: list[str], *indexes: int) -> str:
    return " ".join(columns[index] for index in indexes if index < len(columns) and columns[index])


def _select_file_pairs(files: list[GdeltArchiveFile], *, max_pairs: int) -> list[tuple[GdeltArchiveFile, GdeltArchiveFile]]:
    by_timestamp: dict[str, dict[str, GdeltArchiveFile]] = {}
    for file in files:
        by_timestamp.setdefault(file.timestamp, {})[file.file_type] = file
    pairs = [
        (group["export"], group["mentions"])
        for _, group in sorted(by_timestamp.items())
        if "export" in group and "mentions" in group
    ]
    if max_pairs <= 0 or len(pairs) <= max_pairs:
        return pairs
    if max_pairs == 1:
        return [pairs[-1]]
    step = (len(pairs) - 1) / (max_pairs - 1)
    indexes = sorted({round(index * step) for index in range(max_pairs)})
    return [pairs[index] for index in indexes]


def _fetch_text(url: str, *, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "IranWarCausalTimeline/0.1 local research app"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _fetch_zip_text(url: str, *, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "IranWarCausalTimeline/0.1 local research app"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()
        if not names:
            return ""
        with archive.open(names[0]) as handle:
            return handle.read().decode("utf-8", errors="replace")


def _dedupe_documents(docs: Iterable[SourceDocument]) -> list[SourceDocument]:
    deduped: dict[str, SourceDocument] = {}
    for doc in docs:
        key = _normalized_url(doc.url or doc.id)
        if key not in deduped:
            deduped[key] = doc
    return list(deduped.values())


def _timestamp_to_date(timestamp: str) -> str:
    return f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _normalized_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        path = re.sub(r"/+$", "", parsed.path)
        return f"{parsed.netloc.casefold()}{path.casefold()}"
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _url_signal_text(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        value = f"{parsed.netloc} {parsed.path} {parsed.query}"
    return re.sub(r"[^A-Za-z0-9.]+", " ", unquote(value)).casefold()


def _normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _domain(value: str) -> str:
    return urlparse(value).netloc


def _title_from_url(value: str) -> str:
    parsed = urlparse(value)
    slug = parsed.path.rstrip("/").split("/")[-1]
    slug = re.sub(r"\.[a-z0-9]{2,5}$", "", slug, flags=re.IGNORECASE)
    words = re.sub(r"[-_]+", " ", slug).strip()
    if not words or len(re.sub(r"[^A-Za-z0-9]+", "", words)) < 8:
        return ""
    return words[:1].upper() + words[1:]


def _clip(value: str, limit: int = 700) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
