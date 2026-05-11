# 2026 Iran War Causal Timeline Graph Design

## Summary

Replace the general macro-event workbench with a focused case-study app for the **2026 Iran war**. The app explains what caused the war to start and how it evolved from **December 1, 2025 through the current date** by combining Wikipedia background structure, GDELT timestamped news, Trump/public statement records, Polymarket expectation signals, and FRED oil/equity market series.

The primary experience is a Wikipedia-backed causal graph explaining what caused the war: historical drivers feed strategic drivers, strategic drivers feed proximate rationales/triggers, and those connect to the war start/current state. GDELT, Polymarket, and FRED are supporting layers, not peer content sources in the causal graph. OpenAI structures and labels claims when available; the deterministic fallback must still produce source-backed causal driver nodes from Wikipedia so the app never degrades into a raw source dashboard.

## Product Shape

- Fixed topic: `2026 Iran war`.
- Fixed live evidence window: `2025-12-01` through the app run date.
- Main question: what caused the war to start, which drivers mattered, how did public statements and market reactions evolve, and what is the current state?
- Primary audience: analyst/research user who wants cited causal structure, not a generic summary.
- The existing generic dossier generator should be replaced by this single-case investigation workspace.

## Source Roles

- **Wikipedia** is the historical and narrative backbone.
  - Seed pages include `2026 Iran war`, `Prelude to the 2026 Iran war`, `Rationale for the 2026 Iran war`, `Regime change efforts in the 2026 Iran war`, and `Middle Eastern crisis (2023-present)`.
  - Use `wikipedia-api` for search, page fetches, summaries, sections, links, and categories.
  - Use MediaWiki metadata calls where needed for revision IDs, permanent URLs, timestamps, and provenance.
  - Extract sections such as `Background`, `Prelude`, `Iran nuclear issue`, `Rationale`, `Analysis`, `Economic impacts`, `Energy`, and `Strait of Hormuz`.
- **GDELT** provides timestamped article/story/event evidence from December 2025 onward.
  - Query around Iran, Israel, United States, Strait of Hormuz, nuclear negotiations, sanctions, protests, blockade, ceasefire, oil, and market terms.
  - Use GDELT evidence to support timeline ordering, current-state updates, and news-backed claims.
- **Trump/public statements** capture stance reversals and market-relevant sentiment.
  - Use direct Truth Social URLs where available.
  - Use Trump Archive and GDELT reporting as practical supporting sources.
  - Classify relevant statements as `hawkish`, `dovish`, `ambiguous`, `reversal`, and/or `market_relevant`.
- **Polymarket** provides expectation signals.
  - Include active and closed Iran/Hormuz/nuclear/war markets from December 2025 onward where available.
  - Store status, timing, outcomes, prices/probabilities, resolution state, and source URL.
  - Treat markets as expectation context, not causal proof.
  - Do not promote markets into chronology events by default. Attach them to relevant drivers, scenarios, graph nodes, or claim clusters when mapping is available; otherwise keep them in a supporting prediction-market lane.
- **FRED** provides daily market series.
  - Use `FRED_API_KEY` from `.env`.
  - Brent oil: `DCOILBRENTEU`.
  - WTI oil optional: `DCOILWTICO`.
  - S&P 500: `SP500`.
  - Chart daily values from December 1, 2025 onward with event markers and daily percent moves.
- **OpenAI** structures evidence.
  - Use `OPENAI_API_KEY` from `.env`.
  - The LLM extracts structured events, causes, drivers, rationales, contested interpretations, statement stances, and graph edges.
  - Generated claims without source IDs are rejected.
- **Local NLI** classifies claim-pair relationships before expensive LLM adjudication.
  - Default CPU/dev model: `cross-encoder/nli-deberta-v3-xsmall`.
  - Higher-quality option: `cross-encoder/nli-deberta-v3-base`.
  - Use OpenAI only for low-margin, high-impact, or geopolitically nuanced pairs.

## UI Design

- **Top bar**
  - Title: `2026 Iran War`.
  - Evidence window: `Dec 1, 2025 - current`.
  - Rebuild/refresh control.
  - Source health indicators for Wikipedia, GDELT, Polymarket, FRED, Qdrant, Postgres, and OpenAI.
- **Left panel: Timeline**
  - Lanes separate actual chronology from supporting signals:
    - `Background`: Wikipedia narrative/history anchors.
    - `News reports`: GDELT or statement/news evidence.
    - `Prediction markets`: Polymarket expectation signals; not treated as causes or chronology events.
    - `Market data`: FRED source records that support the market reaction chart.
  - Chronology cards are compact by default: date, title, and source count. Long excerpts belong in the inspector.
  - Selecting a background/news event highlights related graph nodes, edges, and market chart markers when mappings exist.
- **Center panel: Causal graph**
  - The center panel is the primary artifact: a causal graph extracted from the Wikipedia background corpus.
  - Always render driver/rationale/current-state nodes with source-backed claim clusters, even when some edges are low-confidence or fallback-generated.
  - Do not render source-bucket nodes such as `Wikipedia background`, `Polymarket markets`, or `FRED series` as causal graph nodes.
  - Nodes represent structural drivers, strategic drivers, proximate triggers, actor-stated rationales, contested interpretations, opening events, escalation nodes, market reaction nodes, and current-state nodes.
  - Edges use typed relations: `enables`, `pressures`, `justifies`, `triggers`, `escalates`, `constrains`, `contradicts`, `disrupts`, and `correlates_with`.
  - Weakly supported or interpretive edges are visually distinct from directly sourced factual edges.
  - Render with Cytoscape.js inside a React component that owns the Cytoscape instance via `useRef`.
  - React/Zustand state changes should update Cytoscape imperatively through `useEffect`, not by destroying and recreating the graph instance.
  - The default graph view is a backend-precomputed causal spine, not the full graph.
- **Right panel: Evidence inspector**
  - Shows selected node/edge/event detail.
  - Includes source excerpts, URLs, source type, timestamp, Wikipedia page/section/revision, GDELT story/article metadata, statement archive entry, Polymarket market, and FRED data point.
  - Displays claim type and confidence.
- **Bottom panel: Market reaction**
  - Daily chart from December 1, 2025 onward.
  - Series: Brent oil, optional WTI oil, and S&P 500.
  - Overlays markers for opening strikes, ceasefire claims, Hormuz/blockade events, Trump/public statements, Polymarket market resolution/current signals, and large daily moves.
  - Market annotations should state temporal association unless an explicit source attributes the move causally.

## Graph Rendering And Progressive Disclosure

The center graph should use Cytoscape.js as the rendering engine and Zustand for shared selection/filter state.

Rendering rules:

- Keep the Cytoscape instance in a React `useRef`.
- Initialize Cytoscape once when the graph component mounts.
- Update selected nodes, highlighted edges, filters, layout runs, and viewport pan/zoom through imperative `cy` calls inside `useEffect`.
- Do not recreate the Cytoscape instance when a timeline card, market marker, or evidence record is selected.
- Timeline, graph, market chart, and evidence inspector should share one Zustand selection store.

Default graph view:

- The initial graph payload must be the precomputed causal spine, capped around 40-60 visible nodes.
- The backend should mark spine nodes/edges during rebuild using node type, claim confidence, source count, centrality, date importance, and relation type.
- The default visible edge types are `triggers`, `escalates`, `justifies`, and `disrupts`.
- Hide `pressures`, `constrains`, `correlates_with`, low-confidence, superseded, and unresolved edges by default.
- Full graph mode requires explicit user action and should request a separate graph view endpoint rather than being bundled into initial load.

Exploration modes:

- Click a timeline event: highlight related graph node, directly connected edges, and 1-hop neighborhood; pan to the node.
- Shift-click or explicit expand action: load or reveal 2-hop neighborhood.
- Relation filters: toggle causal, contextual, contradiction, and market-correlation edges.
- Claim-status filters: accepted, disputed, superseded, unresolved.
- Entity filters: IRGC, Iran, Israel, Trump, Strait of Hormuz, nuclear program, oil markets, sanctions.
- Dense groups collapse into supernodes such as `Iran nuclear issue`, `Trump statement reversals`, `Hormuz energy risk`, and `Market reactions`.

Layout modes:

- Causal spine: left-to-right layered DAG layout.
- Selected neighborhood: concentric or force-directed local layout around selected node.
- Timeline mode: rank nodes by date bucket from December 2025 to current state.
- Contradiction mode: paired/conflicting clusters connected by `contradicts`, `reversal`, or `superseded` edges.

Visual encoding:

- Node color represents node type.
- Node border represents confidence.
- Dashed edge represents contested or unresolved.
- Red edge represents contradiction.
- Dotted edge represents correlation only.
- Thick edge represents higher-confidence causal relation.
- Node badges show source count and disputed-claim status where relevant.

## Data Model

Canonical records live in Postgres:

- `source_documents`: raw source metadata and excerpts from Wikipedia, GDELT, Polymarket, FRED, and statement archives.
- `source_chunks`: chunked text used for retrieval and LLM extraction.
- `timeline_events`: dated events and background anchors shown in the timeline.
- `graph_nodes`: causal graph nodes.
- `graph_edges`: causal graph relations.
- `market_series_points`: FRED daily market data.
- `statement_signals`: Trump/public statement excerpts and stance classifications.
- `prediction_market_signals`: active/closed Polymarket records.
- `ingestion_runs`: rebuild runs, statuses, timing, and source counts.
- `entities`: canonical actors, places, organizations, systems, and concepts with optional Wikidata QID and Wikipedia page identifiers.
- `entity_aliases`: acronyms, alternate names, translations, descriptors, and observed source forms for canonical entities.
- `entity_mentions`: source-chunk spans that were resolved to canonical entities or retained as unresolved/ambiguous mentions.
- `factual_claims`: atomic claims extracted from source chunks with exact supporting quotes or spans.
- `claim_clusters`: grouped equivalent claims with status `accepted`, `disputed`, `superseded`, or `unresolved`.
- `claim_evidence`: mappings from claims and clusters to source documents and chunks.
- `claim_contradictions`: contradiction, partial-overlap, entailment, or reversal records between claims or clusters.
- `claim_pair_candidates`: blocked candidate pairs selected for local NLI evaluation.
- `claim_adjudications`: OpenAI adjudication records for uncertain or high-impact claim pairs.

Semantic retrieval lives in Qdrant:

- Collection: `iran_war_sources`.
- Payload fields: `source_document_id`, `chunk_id`, `source_type`, `title`, `published_at`, `occurred_at`, `section_title`, `url`, and claim/evidence tags.
- Qdrant is a retrieval index, not the source of truth. It can be rebuilt from Postgres.

## Backend Pipeline

- Load `.env` with `python-dotenv`.
  - Required secret names: `FRED_API_KEY`, `OPENAI_API_KEY`.
  - Never print secret values or return them through APIs.
- Rebuild flow:
  1. Create an `ingestion_run`.
  2. Fetch Wikipedia seed pages and relevant linked pages.
  3. Extract relevant sections and source chunks.
  4. Fetch GDELT stories/events from `2025-12-01` onward.
  5. Fetch Trump/public statement records and supporting news evidence.
  6. Fetch active and closed Polymarket Iran/Hormuz/nuclear/war markets.
  7. Fetch FRED Brent, optional WTI, and S&P 500 daily series.
  8. Embed source chunks and upsert them into Qdrant.
  9. Extract entity mentions and resolve them to canonical entity IDs where confidence is sufficient.
  10. Extract atomic factual claims from source chunks before graph construction, carrying canonical entity IDs where available.
  11. Cluster equivalent claims.
  12. Generate contradiction candidate pairs through canonical entity/date/topic blocking and Qdrant semantic similarity.
  13. Run local NLI on candidate pairs to label `entails`, `contradicts`, `neutral`, or low-confidence.
  14. Apply temporal logic so changed statements across dates become `reversal` or `superseded` when appropriate, not automatic contradiction.
  15. Send only low-margin, high-impact, or geopolitically nuanced pairs to OpenAI adjudication.
  16. Use OpenAI to extract timeline events, graph nodes, graph edges, statement classifications, and market annotations from claim clusters and evidence bundles.
  17. Validate that every generated event/node/edge has source IDs and, where relevant, claim cluster IDs.
  18. Persist accepted records to Postgres and update downstream graph records when claim cluster statuses change.
- Add a dev-only reset command:
  - `python -m backend.app.cli reset-case iran-war`
  - Truncates only this app’s Postgres tables and deletes only Qdrant collection `iran_war_sources`.
  - Does not touch unrelated databases or collections.

## API

- `POST /api/iran-war/rebuild`
  - Starts a rebuild run for the fixed case.
- `GET /api/iran-war`
  - Returns timeline events, precomputed causal-spine graph nodes/edges, current run metadata, and summary state.
- `GET /api/iran-war/graph`
  - Returns named graph views such as `spine`, `neighborhood`, `timeline`, `contradictions`, and `full`.
- `GET /api/iran-war/claims`
  - Returns atomic claims, claim clusters, contradiction status, and supporting source IDs.
- `GET /api/iran-war/sources`
  - Returns source ledger records with filters for source type and date.
- `GET /api/iran-war/market-series`
  - Returns Brent, optional WTI, S&P 500, and chart markers.
- `GET /api/iran-war/source-status`
  - Returns configured/available status for Wikipedia, GDELT, Polymarket, FRED, OpenAI, Postgres, and Qdrant without exposing secret values.

## Guardrails

- Do not present Wikipedia narrative as final authority.
- Separate `reported_fact`, `actor_stated_rationale`, `contested_interpretation`, `market_expectation`, and `model_inference`.
- Do not infer statement-to-market causality from timing alone.
- Use `correlates_with` for temporal alignment unless a source explicitly attributes the market move.
- Reject LLM output that lacks source IDs.
- Do not build causal graph edges directly from raw articles. Build them from accepted or explicitly disputed claim clusters.
- Run entity resolution before claim clustering and semantic blocking so aliases such as `IRGC`, `Islamic Revolutionary Guard Corps`, and source descriptors can map to the same canonical entity when evidence supports it.
- Do not over-resolve ambiguous geopolitical shorthand such as `Tehran`; low-confidence mentions should remain unresolved or ambiguous.
- Preserve contradictions and reversals as first-class evidence instead of collapsing them into a single position.
- Disputed claim clusters may appear in the UI, but graph nodes/edges derived from them must be marked `contested_interpretation` or `unresolved`.
- Keep raw source excerpts short in UI; link to full sources instead.
- Treat Polymarket as expectation data, not proof of cause.

## Entity Resolution

Entity resolution runs before claim extraction, claim clustering, semantic blocking, and local NLI.

The resolver should:

1. Use Wikipedia pages, redirects, linked pages, and Wikidata QIDs as the highest-confidence canonical identifiers.
2. Maintain a case-specific alias seed list for important actors, places, institutions, and concepts:
   - `IRGC`, `Islamic Revolutionary Guard Corps`, `Revolutionary Guards`, `Tehran's elite forces`
   - `IDF`, `Israel Defense Forces`
   - `Strait of Hormuz`, `Hormuz`
   - `IAEA`, `International Atomic Energy Agency`
   - `Trump`, `Donald Trump`, `Truth Social`
   - core actors such as Iran, Israel, United States, Khamenei, Netanyahu, sanctions, nuclear program, ceasefire, blockade, and oil markets
3. Use a rule-based recognizer such as spaCy `EntityRuler` for known aliases and exact phrase patterns.
4. Use NER and Wikipedia/Wikidata search for unresolved mentions.
5. Use OpenAI only for hard descriptors or contextual references, and require it to map to an existing entity or produce a low-confidence unresolved mention.
6. Store unresolved and ambiguous mentions instead of forcing them into canonical entities.

Claims should carry `canonical_entity_ids` where resolution confidence is sufficient. Semantic blocking and contradiction candidate generation should prefer canonical entity IDs over raw strings.

## Contradiction Handling

GDELT and public-statement evidence can contain contradictory or quickly superseded claims. The app should normalize claims before building the causal graph:

1. Extract atomic factual claims from each source chunk, including subject, predicate, object, occurred/published time, exact supporting excerpt, source IDs, and claim type.
2. Cluster claims that refer to the same proposition using canonical entity overlap, date/time proximity, quoted/source overlap, and semantic similarity.
3. Use semantic blocking before pairwise NLI to avoid quadratic comparison costs:
   - identical or overlapping canonical entities
   - nearby dates or same event window
   - matching topic tags
   - high Qdrant vector similarity
   - shared quoted/source material
4. Run a local NLI cross-encoder over blocked candidate pairs and label relationships as `entails`, `contradicts`, `neutral`, or low-confidence.
5. Apply temporal logic over the local NLI result:
   - contradictory claims on the same proposition and same time window become `contradicts`
   - contradictory claims from the same actor across different dates can become `reversal`
   - later sourced corrections can mark earlier clusters as `superseded`
6. Send only low-margin, high-impact, or geopolitically nuanced pairs to OpenAI adjudication.
7. Assign each cluster a status: `accepted`, `disputed`, `superseded`, or `unresolved`.
8. Allow `accepted` clusters to become normal timeline/graph records.
9. Allow `disputed` and `unresolved` clusters only when visibly marked as contested or unresolved.
10. Represent Trump/public-statement flip-flops as temporally ordered stance changes rather than collapsing them into one position.
11. Use source quality as a confidence signal, not as an automatic truth decision.

The graph builder consumes claim clusters and evidence bundles, not raw source documents. A deterministic Wikipedia-backed fallback may generate initial claim clusters directly from Wikipedia sections when OpenAI extraction is unavailable, but those records must still be labeled as extracted claims/drivers and cite source IDs.

## Rebuild Idempotency

The rebuild process must be safe to run daily:

- Source documents and chunks are upserted by stable source key, URL, revision ID, timestamp, or market ID.
- Atomic claims are deduplicated by normalized subject, predicate, object, time window, and supporting source span.
- Entity records and aliases are upserted by stable Wikidata QID, Wikipedia page ID, curated alias key, or normalized source form.
- Claim cluster status can change across rebuilds when new evidence arrives.
- If a cluster changes from `accepted` to `disputed`, `superseded`, or `unresolved`, downstream timeline events and graph edges are updated rather than orphaned.
- UI-facing record IDs should remain stable where the underlying claim cluster remains the same, so selected graph/timeline links do not break unnecessarily.
- Each rebuild stores an `ingestion_run` record with counts for created, updated, superseded, disputed, and rejected records.

## Testing And Acceptance Criteria

- Ingestion tests:
  - Wikipedia section extraction keeps page, section, revision/permalink metadata.
  - GDELT records preserve timestamp, URL, title, and query provenance.
  - FRED parser stores daily Brent and S&P 500 points from `2025-12-01`.
  - Polymarket parser includes both active and closed markets.
- Entity resolution tests:
  - `IRGC`, `Islamic Revolutionary Guard Corps`, and `Revolutionary Guards` resolve to the same canonical entity.
  - Ambiguous shorthand such as `Tehran` can remain unresolved/ambiguous when context does not support a specific actor.
  - Claims carry canonical entity IDs when resolution confidence is sufficient.
- Extraction tests:
  - LLM output without source IDs is rejected.
  - Statement stance labels are constrained to the approved enum.
  - Market annotations default to `correlates_with` unless evidence says otherwise.
  - Atomic claims preserve exact quotes/spans and source chunk IDs.
  - Contradictory claim pairs are stored as contradiction records, not silently merged.
  - Graph records derived from disputed claim clusters are marked as contested or unresolved.
  - Semantic blocking reduces NLI candidate pairs to claims with shared canonical entities, dates, topic tags, or high vector similarity.
  - Low-confidence local NLI pairs are marked unresolved or routed to OpenAI adjudication instead of forced into contradiction.
  - Rebuilds can downgrade an accepted cluster to disputed/superseded and update dependent graph records.
- API tests:
  - `/api/iran-war` returns ordered timeline events and graph records.
  - `/api/iran-war/claims` returns claim clusters and contradiction status without raw secret/config data.
  - `/api/iran-war/market-series` returns chartable series and markers.
  - `/api/iran-war/source-status` never exposes secrets.
- UI tests:
  - Timeline selection highlights related graph and market markers.
  - Cytoscape graph component updates selection and neighborhood highlighting without recreating the graph instance.
  - Default graph payload renders the precomputed causal spine rather than the full graph.
  - Evidence inspector shows source provenance for selected nodes/edges.
  - Market chart renders oil and S&P 500 series with markers.
- Acceptance:
  - The app can rebuild the Iran-war case from configured sources.
  - It displays a dated timeline from December 2025 onward.
  - It displays a causal graph explaining the war’s background, prelude, opening events, and current state.
  - It displays market reaction charts for Brent oil and S&P 500.
  - Every non-market chart node/edge/event has visible source provenance.

## Assumptions

- `.env` contains `FRED_API_KEY` and `OPENAI_API_KEY`.
- Postgres and Qdrant are expected Docker-backed services, but the app must health-check them because they may not be running.
- `docker ps` showed no running containers during design, so implementation should include setup/health checks rather than assuming live services.
- The current generic macro-event workbench can be replaced during implementation.
- The implementation should not delete data from shared Postgres/Qdrant resources except through an explicit app-scoped reset command.
