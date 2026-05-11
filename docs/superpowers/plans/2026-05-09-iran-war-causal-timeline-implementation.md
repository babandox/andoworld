# 2026 Iran War Causal Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic macro-event prototype with a focused 2026 Iran War causal timeline graph app.

**Architecture:** The backend exposes fixed-case `/api/iran-war` endpoints backed by typed domain models, fixture/live-source adapter boundaries, entity resolution, claim clustering, contradiction handling, graph-view generation, and market-series preparation. The frontend is a React workspace with Zustand state, Cytoscape.js graph rendering, a timeline, evidence inspector, and market reaction chart.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, python-dotenv; React, TypeScript, Vite, Vitest, Zustand, Cytoscape.js, lucide-react.

---

### Task 1: Backend Replacement

**Files:**
- Replace: `backend/app/models.py`
- Create: `backend/app/iran_war/*.py`
- Replace: `backend/app/main.py`
- Replace tests under `backend/tests/`

- [ ] Write failing tests for entity resolution, claim contradiction handling, graph spine generation, market series markers, and API contracts.
- [ ] Implement domain models for sources, entities, claims, graph records, market series, and source status.
- [ ] Implement fixture-backed case repository with extension points for Wikipedia, GDELT, Polymarket, FRED, OpenAI, Postgres, and Qdrant.
- [ ] Implement entity resolver with curated aliases and ambiguous mention handling.
- [ ] Implement claim clustering, semantic-blocking candidate selection, deterministic NLI fallback, temporal reversal/supersession logic, and graph-view builder.
- [ ] Implement FastAPI endpoints: `/api/iran-war`, `/api/iran-war/graph`, `/api/iran-war/claims`, `/api/iran-war/sources`, `/api/iran-war/market-series`, `/api/iran-war/source-status`, `/api/iran-war/rebuild`.
- [ ] Run `python -m pytest backend/tests -q`.

### Task 2: Frontend Replacement

**Files:**
- Replace: `frontend/src/App.tsx`
- Replace/Create: `frontend/src/*.ts`
- Replace: `frontend/src/App.css`
- Update: `frontend/package.json`

- [ ] Write failing tests for graph payload filtering and market-series formatting.
- [ ] Implement API types and client functions for the fixed Iran-war endpoints.
- [ ] Implement Zustand selection/filter store.
- [ ] Implement timeline, Cytoscape graph component, evidence inspector, market chart, and source status top bar.
- [ ] Ensure Cytoscape is created once with `useRef` and updated imperatively from Zustand state.
- [ ] Run `npm test -- --run` and `npm run build`.

### Task 3: Verification And Run

- [ ] Run backend tests.
- [ ] Run frontend tests.
- [ ] Run frontend build.
- [ ] Start backend and frontend dev servers.
- [ ] Verify `/api/iran-war`, `/api/iran-war/graph?view=spine`, `/api/iran-war/claims`, and the frontend root respond.

### Constraints

- Do not print `.env` secret values.
- Do not delete `.env`.
- If Docker Postgres/Qdrant are not running, return source-status as unavailable and use fixture-backed data.
- Full graph is not initial payload; initial app load uses the causal spine.
