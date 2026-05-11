from backend.app.iran_war.gdelt_backfill import GdeltBackfillOptions, run_gdelt_backfill
from backend.app.iran_war.backfill_gdelt import parse_options


def gdelt_manifest(*timestamps: str) -> str:
    lines: list[str] = []
    for timestamp in timestamps:
        lines.append(f"39726 abc http://data.gdeltproject.org/gdeltv2/{timestamp}.export.CSV.zip")
        lines.append(f"58092 def http://data.gdeltproject.org/gdeltv2/{timestamp}.mentions.CSV.zip")
    return "\n".join(lines)


def export_row(event_id: str, timestamp: str, url: str) -> str:
    columns = [""] * 61
    columns[0] = event_id
    columns[1] = timestamp[:8]
    columns[6] = "IRAN"
    columns[7] = "IRN"
    columns[16] = "ISRAEL"
    columns[17] = "ISR"
    columns[26] = "190"
    columns[28] = "19"
    columns[29] = "4"
    columns[30] = "-10.0"
    columns[34] = "-6.0"
    columns[59] = timestamp
    columns[60] = url
    return "\t".join(columns)


def mentions_row(event_id: str, timestamp: str, url: str) -> str:
    columns = [""] * 16
    columns[0] = event_id
    columns[2] = timestamp
    columns[4] = "wire.test"
    columns[5] = url
    columns[11] = "90"
    columns[13] = "-6.0"
    return "\t".join(columns)


def test_gdelt_backfill_dry_run_processes_pairs_without_persisting():
    timestamp = "20260302120000"
    manifest = gdelt_manifest(timestamp)
    export_url = f"http://data.gdeltproject.org/gdeltv2/{timestamp}.export.CSV.zip"
    mentions_url = f"http://data.gdeltproject.org/gdeltv2/{timestamp}.mentions.CSV.zip"
    payloads = {
        export_url: export_row("1", timestamp, "https://wire.test/iran-missile-strike-israel"),
        mentions_url: mentions_row("1", timestamp, "https://wire.test/iran-missile-strike-israel"),
    }
    persisted: list[int] = []

    stats = run_gdelt_backfill(
        GdeltBackfillOptions(start="2026-03-02", end="2026-03-02", dry_run=True),
        manifest_text=manifest,
        zip_text_fetcher=lambda url, timeout: payloads[url],
        persist_documents=lambda docs: persisted.append(len(docs)) or None,
    )

    assert stats.pairs_available == 1
    assert stats.pairs_processed == 1
    assert stats.source_documents == 1
    assert stats.persisted_documents == 0
    assert persisted == []


def test_gdelt_backfill_persists_in_batches():
    timestamps = ["20260302120000", "20260302121500", "20260302123000"]
    manifest = gdelt_manifest(*timestamps)
    payloads: dict[str, str] = {}
    for index, timestamp in enumerate(timestamps, start=1):
        url = f"https://wire.test/iran-missile-strike-israel-{index}"
        payloads[f"http://data.gdeltproject.org/gdeltv2/{timestamp}.export.CSV.zip"] = export_row(str(index), timestamp, url)
        payloads[f"http://data.gdeltproject.org/gdeltv2/{timestamp}.mentions.CSV.zip"] = mentions_row(str(index), timestamp, url)
    batch_sizes: list[int] = []

    stats = run_gdelt_backfill(
        GdeltBackfillOptions(start="2026-03-02", end="2026-03-02", batch_size=2),
        manifest_text=manifest,
        zip_text_fetcher=lambda url, timeout: payloads[url],
        persist_documents=lambda docs: batch_sizes.append(len(docs)) or None,
    )

    assert stats.source_documents == 3
    assert stats.persisted_documents == 3
    assert batch_sizes == [2, 1]


def test_gdelt_backfill_resume_after_timestamp_skips_older_pairs():
    timestamps = ["20260302120000", "20260302121500", "20260302123000"]
    manifest = gdelt_manifest(*timestamps)
    payloads: dict[str, str] = {}
    for index, timestamp in enumerate(timestamps, start=1):
        url = f"https://wire.test/iran-missile-strike-israel-{index}"
        payloads[f"http://data.gdeltproject.org/gdeltv2/{timestamp}.export.CSV.zip"] = export_row(str(index), timestamp, url)
        payloads[f"http://data.gdeltproject.org/gdeltv2/{timestamp}.mentions.CSV.zip"] = mentions_row(str(index), timestamp, url)

    stats = run_gdelt_backfill(
        GdeltBackfillOptions(
            start="2026-03-02",
            end="2026-03-02",
            resume_after_timestamp="20260302121500",
            dry_run=True,
        ),
        manifest_text=manifest,
        zip_text_fetcher=lambda url, timeout: payloads[url],
    )

    assert stats.pairs_available == 3
    assert stats.pairs_processed == 1
    assert stats.last_timestamp == "20260302123000"


def test_gdelt_backfill_continues_after_pair_error():
    timestamps = ["20260302120000", "20260302121500"]
    manifest = gdelt_manifest(*timestamps)
    good_export_url = "http://data.gdeltproject.org/gdeltv2/20260302121500.export.CSV.zip"
    good_mentions_url = "http://data.gdeltproject.org/gdeltv2/20260302121500.mentions.CSV.zip"

    def fetcher(url: str, timeout: float) -> str:
        if "20260302120000" in url:
            raise TimeoutError("slow archive")
        if url == good_export_url:
            return export_row("2", "20260302121500", "https://wire.test/iran-missile-strike-israel")
        if url == good_mentions_url:
            return mentions_row("2", "20260302121500", "https://wire.test/iran-missile-strike-israel")
        raise AssertionError(url)

    stats = run_gdelt_backfill(
        GdeltBackfillOptions(start="2026-03-02", end="2026-03-02", dry_run=True),
        manifest_text=manifest,
        zip_text_fetcher=fetcher,
    )

    assert stats.pairs_available == 2
    assert stats.pairs_processed == 1
    assert stats.source_documents == 1
    assert len(stats.errors) == 1
    assert "20260302120000" in stats.errors[0]


def test_gdelt_backfill_cli_parses_dry_run_options():
    options = parse_options(
        [
            "--start",
            "2025-12-01",
            "--end",
            "2026-05-11",
            "--limit-pairs",
            "10",
            "--resume-after-timestamp",
            "20260302120000",
            "--batch-size",
            "50",
            "--timeout",
            "30",
            "--dry-run",
        ]
    )

    assert options == GdeltBackfillOptions(
        start="2025-12-01",
        end="2026-05-11",
        limit_pairs=10,
        resume_after_timestamp="20260302120000",
        batch_size=50,
        timeout=30.0,
        dry_run=True,
    )
