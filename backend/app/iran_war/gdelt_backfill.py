from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from backend.app.iran_war.gdelt_raw import (
    GdeltArchiveFile,
    MASTERFILELIST_URL,
    RawGdeltMention,
    _fetch_text,
    _fetch_zip_text,
    build_gdelt_source_documents,
    parse_gdelt_export_rows,
    parse_gdelt_masterfilelist,
    parse_gdelt_mentions_rows,
)
from backend.app.iran_war.persistence import persist_source_documents
from backend.app.models import SourceDocument


ZipTextFetcher = Callable[[str, float], str]
PersistDocuments = Callable[[list[SourceDocument]], None]


@dataclass(frozen=True)
class GdeltBackfillOptions:
    start: str
    end: str
    limit_pairs: int | None = None
    resume_after_timestamp: str | None = None
    batch_size: int = 250
    timeout: float = 20.0
    dry_run: bool = False


@dataclass
class GdeltBackfillStats:
    pairs_available: int = 0
    pairs_processed: int = 0
    source_documents: int = 0
    persisted_documents: int = 0
    errors: list[str] = field(default_factory=list)
    first_timestamp: str | None = None
    last_timestamp: str | None = None


def run_gdelt_backfill(
    options: GdeltBackfillOptions,
    *,
    manifest_text: str | None = None,
    zip_text_fetcher: ZipTextFetcher | None = None,
    persist_documents: PersistDocuments | None = None,
) -> GdeltBackfillStats:
    fetch_zip = zip_text_fetcher or (lambda url, timeout: _fetch_zip_text(url, timeout=timeout))
    persist = persist_documents or _default_persist_documents
    manifest = manifest_text if manifest_text is not None else _fetch_text(MASTERFILELIST_URL, timeout=options.timeout)
    files = parse_gdelt_masterfilelist(manifest, start=options.start, end=options.end, file_types={"export", "mentions"})
    pairs = _archive_file_pairs(files)

    stats = GdeltBackfillStats(pairs_available=len(pairs))
    pending: list[SourceDocument] = []
    selected_pairs = _select_backfill_pairs(pairs, options)
    for export_file, mentions_file in selected_pairs:
        try:
            docs = _documents_for_pair(export_file, mentions_file, zip_text_fetcher=fetch_zip, timeout=options.timeout)
        except Exception as exc:
            stats.errors.append(f"GDELT raw backfill {export_file.timestamp}: {type(exc).__name__}")
            continue

        stats.pairs_processed += 1
        stats.source_documents += len(docs)
        stats.first_timestamp = stats.first_timestamp or export_file.timestamp
        stats.last_timestamp = export_file.timestamp
        if options.dry_run:
            continue
        pending.extend(docs)
        if len(pending) >= options.batch_size:
            _persist_batch(pending, persist, stats)
            pending = []

    if pending and not options.dry_run:
        _persist_batch(pending, persist, stats)
    return stats


def _documents_for_pair(
    export_file: GdeltArchiveFile,
    mentions_file: GdeltArchiveFile,
    *,
    zip_text_fetcher: ZipTextFetcher,
    timeout: float,
) -> list[SourceDocument]:
    export_text = zip_text_fetcher(export_file.url, timeout)
    events = parse_gdelt_export_rows(export_text, limit=10000)
    if not events:
        return []
    mentions_text = zip_text_fetcher(mentions_file.url, timeout)
    mentions: dict[str, list[RawGdeltMention]] = parse_gdelt_mentions_rows(
        mentions_text,
        event_ids={event.event_id for event in events},
    )
    retrieved_at = datetime.now(timezone.utc).date().isoformat()
    return build_gdelt_source_documents(events, mentions, retrieved_at=retrieved_at, limit=10000)


def _archive_file_pairs(files: list[GdeltArchiveFile]) -> list[tuple[GdeltArchiveFile, GdeltArchiveFile]]:
    by_timestamp: dict[str, dict[str, GdeltArchiveFile]] = {}
    for file in files:
        by_timestamp.setdefault(file.timestamp, {})[file.file_type] = file
    return [
        (group["export"], group["mentions"])
        for _, group in sorted(by_timestamp.items())
        if "export" in group and "mentions" in group
    ]


def _select_backfill_pairs(
    pairs: list[tuple[GdeltArchiveFile, GdeltArchiveFile]],
    options: GdeltBackfillOptions,
) -> list[tuple[GdeltArchiveFile, GdeltArchiveFile]]:
    selected = [
        pair
        for pair in pairs
        if not options.resume_after_timestamp or pair[0].timestamp > options.resume_after_timestamp
    ]
    if options.limit_pairs is None:
        return selected
    return selected[: max(0, options.limit_pairs)]


def _persist_batch(
    docs: list[SourceDocument],
    persist: PersistDocuments,
    stats: GdeltBackfillStats,
) -> None:
    if not docs:
        return
    persist(docs)
    stats.persisted_documents += len(docs)


def _default_persist_documents(docs: list[SourceDocument]) -> None:
    result = persist_source_documents(docs)
    if not result.postgres_available:
        raise RuntimeError(result.postgres_note)
