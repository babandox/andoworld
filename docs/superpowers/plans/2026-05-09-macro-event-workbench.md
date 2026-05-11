# Macro Event Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable V1 that generates analyst-facing macro-event dossiers with cited causal timelines, type-specific scenarios, and strict uncertainty separation.

**Architecture:** A FastAPI backend owns ingestion adapters, deterministic fallback reasoning, dossier persistence, and JSON APIs. A React/Vite frontend renders the dossier, causal graph preview, scenario tree, probability panel, and source ledger. Live GDELT/OpenAI/Polymarket integrations are optional; without credentials the app uses transparent fixture-backed analysis.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest; React, TypeScript, Vite, Vitest.

---

## File Structure

- `backend/app/models.py`: Pydantic request/response and domain models.
- `backend/app/scenarios.py`: Event-type-specific scenario templates.
- `backend/app/fixtures.py`: Small deterministic evidence set for local demos and tests.
- `backend/app/adapters/gdelt.py`: GDELT response parsing and optional HTTP fetch.
- `backend/app/adapters/polymarket.py`: Polymarket response parsing and optional HTTP fetch.
- `backend/app/reasoning.py`: Evidence-grounded deterministic causal/scenario synthesis with optional OpenAI interface boundary.
- `backend/app/pipeline.py`: Dossier creation, storage, and retrieval orchestration.
- `backend/app/main.py`: FastAPI routes.
- `backend/tests/*.py`: Backend contract tests.
- `frontend/src/*`: React dossier UI, API client, types, formatting helpers, and styles.

## Tasks

### Task 1: Backend Contracts

- [ ] Write failing tests for scenario templates, adapter parsing, dossier generation, and API routes.
- [ ] Implement Pydantic models and scenario templates.
- [ ] Implement GDELT and Polymarket parsers.
- [ ] Implement deterministic dossier pipeline with evidence references on every causal claim.
- [ ] Implement FastAPI routes for `POST /api/dossiers`, `GET /api/dossiers/{id}`, and `GET /api/dossiers/{id}/sources`.
- [ ] Run `python -m pytest backend/tests -q`.

### Task 2: Frontend Dossier UI

- [ ] Write failing frontend tests for formatting helpers and branch likelihood labels.
- [ ] Create a Vite React app shell with API client and type definitions.
- [ ] Implement a dossier creation form and a dossier page with timeline, causal claims, scenario branches, probability panel, limitations, and source ledger.
- [ ] Run `npm test -- --run` in `frontend`.

### Task 3: End-to-End Verification

- [ ] Install frontend dependencies with `npm install`.
- [ ] Run backend and frontend tests.
- [ ] Start the backend and frontend dev servers.
- [ ] Verify the user can open the React app and create a fixture-backed dossier without API keys.
