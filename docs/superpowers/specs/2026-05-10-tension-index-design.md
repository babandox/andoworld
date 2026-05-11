# Tension Index Design

## Goal

Add a source-backed daily US/Israel-Iran tension line below the Brent, WTI, and S&P 500 market rows.

## Design

The first version is deterministic and auditable. It derives a `0-100` daily tension index from dated case evidence, especially Wikipedia reference citations and GDELT records. Each contributing event receives a signed weight from transparent keyword rules:

- Major escalation: strikes, missiles, direct attacks, facilities targeted, war declarations.
- Moderate escalation: blockade, Hormuz closure, airspace closure, military deployments, shipping threats.
- Rhetorical escalation: Trump/public threats, regime-change rhetoric, warning statements.
- De-escalation: ceasefire, peace deal, talks, inspections, restraint, lifted blockade.
- Uncertainty: disputed or unclear reports with smaller weight.

The daily score starts from a neutral baseline, applies each day's weighted deltas, decays gently toward neutral on quiet days, and clamps to `0-100`. Each point stores contributor `source_ids`, so the line is inspectable and can later be upgraded to an OpenAI classifier without changing the chart contract.

## Data Contract

Backend adds `tension_series` to `IranWarCase`:

- `date`: ISO day.
- `value`: normalized tension score from `0` to `100`.
- `source`: `rule_based`.
- `source_ids`: sources contributing on that date.
- `summary`: short explanation of the day's movement.

Frontend renders this as a fourth row in the existing market chart, sharing the same date window and event rug.

## Scope

This does not use Polymarket as an input. Prediction markets remain scenario expectations. The line uses only dated evidence sources.
