# Tension Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-backed daily US/Israel-Iran tension line under the market chart.

**Architecture:** The backend computes a deterministic daily tension index from dated source documents and exposes it in the main case payload. The frontend renders it as a fourth small-multiple row sharing the market chart window and evidence rug.

**Tech Stack:** Python/Pydantic/FastAPI backend, React/TypeScript/Vitest frontend, SVG chart rendering.

---

### Task 1: Backend Data Model And Scoring

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/iran_war/tension.py`
- Test: `backend/tests/test_iran_war_tension.py`

- [ ] **Step 1: Write failing tests**

Add tests proving escalation raises the line, ceasefire lowers it, points keep source IDs, and sparse days decay toward neutral.

- [ ] **Step 2: Implement model and scorer**

Add `TensionSeriesPoint` with `date`, `value`, `source`, `source_ids`, and `summary`. Implement deterministic scoring in `tension.py`.

- [ ] **Step 3: Verify backend tests**

Run `PYTHONPATH=. pytest backend/tests/test_iran_war_tension.py -q`.

### Task 2: Case And API Wiring

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/iran_war/case_builder.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_iran_war_api.py`

- [ ] **Step 1: Write failing API/case tests**

Assert `IranWarCase` includes `tension_series` and `/api/iran-war/market-series` returns it alongside market series and markers.

- [ ] **Step 2: Wire scorer into case builder**

Call the scorer using `timeline_events` plus source documents after ingestion and fixture fallback.

- [ ] **Step 3: Verify backend suite**

Run `PYTHONPATH=. pytest backend/tests -q`.

### Task 3: Frontend Rendering

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/market.ts`
- Modify: `frontend/src/market.test.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Write failing frontend tests**

Assert tension points can be windowed and rendered as an indexed/non-indexed row without changing market rows.

- [ ] **Step 2: Add TypeScript types and chart row**

Add `TensionSeriesPoint` and render `Tension` as a fourth row below S&P 500.

- [ ] **Step 3: Verify frontend**

Run `npm test -- --run` and `npm run build` in `frontend`.

### Task 4: Rebuild Local Case

**Files:**
- No code changes.

- [ ] **Step 1: Restart backend**

Restart uvicorn on `127.0.0.1:8000`.

- [ ] **Step 2: Rebuild case**

POST `/api/iran-war/rebuild` and confirm `tension_series` spans the same evidence window as the market chart.
