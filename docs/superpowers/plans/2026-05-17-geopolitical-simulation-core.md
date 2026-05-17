# Geopolitical Simulation Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Python backend slice from `deep_research_plan.md`: in-memory graph simulation, seven mathematical theory modules, and an SMC particle core.

**Architecture:** Use a small Python package under `src/andoworldstate` with a graph boundary, one module per theory, and a generic SMC module. Keep the slice dependency-light and Mesa-compatible without requiring Mesa or Neo4j yet.

**Tech Stack:** Python 3.11, pytest, standard-library dataclasses/math/random/copy.

---

## File Structure

- Create: `pyproject.toml` for pytest configuration and package metadata.
- Create: `src/andoworldstate/graph.py` for the in-memory graph boundary.
- Create: `src/andoworldstate/smc.py` for particles, normalization, effective sample size, and systematic resampling.
- Create: `src/andoworldstate/theories/agent_zero.py` for Epstein Agent Zero.
- Create: `src/andoworldstate/theories/structural_demographic.py` for Turchin SDT.
- Create: `src/andoworldstate/theories/poliheuristic.py` for Mintz PH.
- Create: `src/andoworldstate/theories/watts.py` for Watts threshold cascades.
- Create: `src/andoworldstate/theories/moran.py` for Nowak death-Birth dynamics.
- Create: `src/andoworldstate/theories/complex_contagion.py` for Centola complex contagion.
- Create: `src/andoworldstate/theories/fast_frugal.py` for Gigerenzer FFTs.
- Create: tests under `tests/` matching each module.

## Tasks

### Task 1: Tests And Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `tests/test_agent_zero.py`
- Create: `tests/test_structural_demographic.py`
- Create: `tests/test_poliheuristic.py`
- Create: `tests/test_watts.py`
- Create: `tests/test_moran.py`
- Create: `tests/test_complex_contagion.py`
- Create: `tests/test_fast_frugal.py`
- Create: `tests/test_smc.py`

- [ ] **Step 1: Write failing tests**

Tests must assert the plan's formulas: Rescorla-Wagner update, PSI multiplication, noncompensatory pruning, fractional threshold activation, death-Birth weighted replacement, complex contagion reinforcement threshold, FFT early exits, and SMC normalization/resampling.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest`

Expected: FAIL because `andoworldstate` modules do not exist yet.

### Task 2: Graph Boundary

**Files:**
- Create: `src/andoworldstate/__init__.py`
- Create: `src/andoworldstate/graph.py`
- Test: `tests/test_agent_zero.py`, `tests/test_moran.py`, `tests/test_complex_contagion.py`

- [ ] **Step 1: Implement `InMemoryGraph`**

Provide `add_node`, `set_node_property`, `node_properties`, `add_edge`, `neighbors`, `edge_property`, `degree`, and `edges_between`.

- [ ] **Step 2: Run graph-dependent tests**

Run: `python -m pytest tests/test_agent_zero.py tests/test_moran.py tests/test_complex_contagion.py`

Expected: theory imports still fail until later tasks.

### Task 3: Theory Modules

**Files:**
- Create: all files in `src/andoworldstate/theories/`
- Test: all `tests/test_*.py` except `tests/test_smc.py`

- [ ] **Step 1: Implement each theory exactly from the design**

Keep each module focused on one framework and expose only the functions/classes used in tests.

- [ ] **Step 2: Run theory tests**

Run: `python -m pytest tests/test_agent_zero.py tests/test_structural_demographic.py tests/test_poliheuristic.py tests/test_watts.py tests/test_moran.py tests/test_complex_contagion.py tests/test_fast_frugal.py`

Expected: PASS.

### Task 4: SMC Core

**Files:**
- Create: `src/andoworldstate/smc.py`
- Test: `tests/test_smc.py`

- [ ] **Step 1: Implement particles and resampling**

Implement non-negative weight validation, normalization, effective sample size, and deterministic systematic resampling with a supplied start offset.

- [ ] **Step 2: Run SMC tests**

Run: `python -m pytest tests/test_smc.py`

Expected: PASS.

### Task 5: Full Verification

**Files:**
- Modify only if tests expose a plan-alignment issue.

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest`

Expected: PASS.

- [ ] **Step 2: Check drift from `deep_research_plan.md`**

Confirm the implementation has no UI, no live ingestion, no direct Neo4j driver, no LLM agent loop, and no unplanned scoring layer.
