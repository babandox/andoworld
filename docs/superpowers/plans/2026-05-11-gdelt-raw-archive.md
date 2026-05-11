# GDELT Raw Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bounded raw GDELT archive ingestion path using masterfilelist export/mentions files.

**Architecture:** Create a focused `backend/app/iran_war/gdelt_raw.py` module that parses manifests, filters raw events, joins mentions, and emits `SourceDocument`s. Wire `ingest_gdelt()` to try raw archive ingestion first and fall back to the current DOC API.

**Tech Stack:** Python stdlib `zipfile`, `csv`, `urllib`, existing FastAPI backend models/tests.

---

### Task 1: Parser And Filter Tests

**Files:**
- Modify: `backend/tests/test_iran_war_ingestion.py`

- [ ] Add tests for manifest parsing, raw export row relevance, mention joins, and document conversion.
- [ ] Run: `python -m pytest backend\tests\test_iran_war_ingestion.py -k gdelt_raw`
- [ ] Expected: tests fail because `backend.app.iran_war.gdelt_raw` does not exist.

### Task 2: Raw Archive Module

**Files:**
- Create: `backend/app/iran_war/gdelt_raw.py`

- [ ] Implement `parse_gdelt_masterfilelist`.
- [ ] Implement `parse_gdelt_export_rows`.
- [ ] Implement `parse_gdelt_mentions_rows`.
- [ ] Implement `build_gdelt_source_documents`.
- [ ] Implement `ingest_gdelt_raw_archive` with a configurable file-pair cap.
- [ ] Run: `python -m pytest backend\tests\test_iran_war_ingestion.py -k gdelt_raw`
- [ ] Expected: raw GDELT tests pass.

### Task 3: Wire Into Existing Ingestion

**Files:**
- Modify: `backend/app/iran_war/ingestion.py`
- Modify: `backend/tests/test_iran_war_ingestion.py`

- [ ] Make `ingest_gdelt()` call `ingest_gdelt_raw_archive()` first.
- [ ] If raw archive returns documents, return those documents and preserve non-fatal warnings.
- [ ] If raw archive returns no documents or errors, keep the current DOC API path.
- [ ] Run: `python -m pytest backend\tests`
- [ ] Expected: backend tests pass.

### Task 4: Live Smoke Test

**Files:**
- No code changes unless the smoke test exposes a failing behavior.

- [ ] Run a small capped raw archive sample against the live manifest.
- [ ] Confirm the command returns either relevant GDELT source documents or a clear non-secret error.
- [ ] Restart the backend if code changed after it was already running.
