# GDELT Export Mentions Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable command that backfills filtered GDELT `export.CSV.zip` + `mentions.CSV.zip` records for the Iran conflict into Postgres.

**Architecture:** Keep runtime ingestion capped, and add a separate `gdelt_backfill.py` runner for bulk archive work. The runner reads the masterfilelist, pairs export/mentions archives by timestamp, processes pairs sequentially, persists filtered `SourceDocument` records in batches, and prints progress stats.

**Tech Stack:** Python stdlib, existing `gdelt_raw.py` parser/filter, existing Postgres persistence helpers.

---

### Task 1: Backfill Runner Tests

**Files:**
- Create: `backend/tests/test_iran_war_gdelt_backfill.py`

- [ ] Add tests for pair processing, batch persistence, and dry-run behavior.
- [ ] Run: `python -m pytest backend\tests\test_iran_war_gdelt_backfill.py`
- [ ] Expected: fail because the backfill module does not exist.

### Task 2: Backfill Module

**Files:**
- Create: `backend/app/iran_war/gdelt_backfill.py`

- [ ] Implement `GdeltBackfillOptions`, `GdeltBackfillStats`, and `run_gdelt_backfill`.
- [ ] Implement injectable fetch and persist callables so tests avoid network/database.
- [ ] Run: `python -m pytest backend\tests\test_iran_war_gdelt_backfill.py`
- [ ] Expected: pass.

### Task 3: Persistence Hook

**Files:**
- Modify: `backend/app/iran_war/persistence.py`

- [ ] Add `persist_source_documents(source_documents)`.
- [ ] Reuse existing table creation/upsert behavior with `prune_missing=False`.
- [ ] Run: `python -m pytest backend\tests`.
- [ ] Expected: pass.

### Task 4: CLI Entry

**Files:**
- Create: `backend/app/iran_war/backfill_gdelt.py`

- [ ] Add `python -m backend.app.iran_war.backfill_gdelt --start 2025-12-01 --end 2026-05-11 --limit-pairs 10 --dry-run`.
- [ ] Print JSON stats only, with no secrets.
- [ ] Run a dry-run sample.
