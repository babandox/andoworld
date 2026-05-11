from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import json
import sys

from backend.app.iran_war.config import load_env_file
from backend.app.iran_war.gdelt_backfill import GdeltBackfillOptions, run_gdelt_backfill
from backend.app.iran_war.ingestion import EVIDENCE_START


def parse_options(argv: list[str] | None = None) -> GdeltBackfillOptions:
    parser = argparse.ArgumentParser(description="Backfill filtered GDELT export+mentions archive records for the Iran conflict.")
    parser.add_argument("--start", default=EVIDENCE_START, help="Inclusive ISO start date, for example 2025-12-01.")
    parser.add_argument("--end", default=datetime.now(timezone.utc).date().isoformat(), help="Inclusive ISO end date.")
    parser.add_argument("--limit-pairs", type=int, default=None, help="Maximum number of 15-minute export/mentions pairs to process.")
    parser.add_argument("--resume-after-timestamp", default=None, help="Skip archive pairs at or before this GDELT timestamp.")
    parser.add_argument("--batch-size", type=int, default=250, help="Postgres upsert batch size.")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout per manifest/archive request.")
    parser.add_argument("--dry-run", action="store_true", help="Process archives but do not write records to Postgres.")
    args = parser.parse_args(argv)
    return GdeltBackfillOptions(
        start=args.start,
        end=args.end,
        limit_pairs=args.limit_pairs,
        resume_after_timestamp=args.resume_after_timestamp,
        batch_size=args.batch_size,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    options = parse_options(argv)
    stats = run_gdelt_backfill(options)
    print(json.dumps(asdict(stats), indent=2, sort_keys=True))
    return 1 if stats.errors and stats.pairs_processed == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
