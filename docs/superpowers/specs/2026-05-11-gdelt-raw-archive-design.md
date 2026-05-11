# GDELT Raw Archive Ingestion Design

## Goal

Use GDELT's raw 15-minute archive files as a fallback-quality source for Iran conflict reporting when the DOC API returns gaps or rate limits.

## Design

The app will read `masterfilelist.txt`, select `.export.CSV.zip` and `.mentions.CSV.zip` files in the evidence window, stream the zipped tab-delimited rows, and filter records to the Iran conflict. The first pass will not ingest `.gkg.csv.zip`; GKG is larger and should be added only after export/mentions filtering is stable.

The raw archive path returns normal `SourceDocument(source_type="gdelt")` records. Each document is based on a relevant GDELT event plus its mention/article URL when available. Relevance is deterministic: Iran/Israel/US actors and conflict/diplomacy event codes are weighted together with URL/text keywords such as Hormuz, nuclear, missile, strike, ceasefire, Trump, IRGC, and Hezbollah.

## Scope

This is not a full historical backfill daemon. Runtime ingestion uses a configurable cap on archive file pairs to avoid downloading gigabytes during page load. A later batch command can exhaustively process December 2025 through today into Postgres.

## Data Contract

The existing case builder receives GDELT raw archive matches as `SourceDocument` records with:

- `id`: stable `gdelt:` hash.
- `source_type`: `gdelt`.
- `title`: URL-derived article label or event label.
- `url`: mention URL or source URL.
- `published_at`: GDELT mention/event timestamp.
- `excerpt`: event actors, event code, Goldstein score, tone, and archive source.

## Error Handling

If the manifest or archive files fail, ingestion records a clear `GDELT raw archive failed: ...` error and falls back to the existing DOC API path.
