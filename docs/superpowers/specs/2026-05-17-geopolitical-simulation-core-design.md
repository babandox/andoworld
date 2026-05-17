# Geopolitical Simulation Core Design

## Source Of Truth

This design implements the first backend slice approved from `deep_research_plan.md`: a Python simulation core that validates the plan's deterministic and probabilistic mathematics in memory before attaching Neo4j, live data feeds, or a user interface.

The implementation must not introduce LLM agents, subjective scoring, UI workflows, live OSINT ingestion, or direct Neo4j persistence in this slice.

## Architecture

The core is a Python package with focused modules for the seven frameworks in the research plan and a small Sequential Monte Carlo layer that can weight, normalize, and resample particles. Agents expose simple Mesa-style state and `step` behavior, but the first slice does not depend on Mesa being installed. This keeps the math testable in the current workspace while preserving a straightforward path to Mesa integration later.

The graph boundary is an in-memory adapter with Neo4j-compatible concepts: node properties, directed relationships, edge weights, neighbor traversal, degree queries, and bridge-width queries. Theory modules depend on that boundary rather than a database driver.

## Theory Modules

Agent Zero implements Rescorla-Wagner affective updates, localized cognitive risk assignment supplied by the caller, weighted social contagion over graph neighbors, binary activation when total disposition exceeds the activation threshold, and Gaussian particle weighting against observed protest volume.

Structural-Demographic Theory implements Mass Mobilization Potential, Elite Mobilization Potential, State Fiscal Distress, the multiplicative Political Stress Indicator, logistic instability mapping, hard assimilation of observed macro variables, and exponential particle penalization by observed instability divergence.

Poliheuristic Theory implements noncompensatory first-stage political survival pruning, second-stage expected utility over surviving options, and the fallback that chooses the least politically damaging option when every option is below threshold.

Watts cascade dynamics implement fractional threshold activation based on the active-neighbor ratio, vulnerable-node detection where one active neighbor can trigger activation, and Gaussian-kernel particle weighting against observed cascade size.

Nowak evolutionary graph dynamics implement the death-Birth Moran process from the plan: select a collapsed node, compute neighbor replacement probabilities from `fitness * logistical_weight`, and copy the victor's ideology and fitness into the collapsed node.

Centola complex contagion implements absolute reinforcement thresholds greater than one, adoption only when independent active signals meet the threshold, and bridge-width measurement across communities.

Gigerenzer fast-and-frugal trees implement lexicographic cue evaluation, immediate exit on triggered non-final cues, and forced binary classification at the final cue.

## Sequential Monte Carlo

A particle owns model state and a non-negative importance weight. The SMC layer normalizes weights, computes effective sample size, performs systematic resampling, and accepts theory-specific weighting functions. Mutation is represented as an optional callback so the math core does not invent mutation rules not specified in the research plan.

## Data Flow

Tests or later ingestion adapters provide empirical observations. Theory modules assimilate the exact variables described in the plan, update internal state, and return likelihood-adjusted weights. The SMC layer normalizes and resamples based on those weights.

## Error Handling

The core raises explicit `ValueError` exceptions for invalid mathematical inputs such as zero variance, negative weights, empty option sets, empty FFT cue hierarchies, missing graph nodes, and zero denominators in probabilistic replacement. It does not silently coerce invalid model states.

## Testing

Tests are formula-first. Each framework has tests for its defining equations and decision boundaries. SMC tests cover normalization, effective sample size, and deterministic systematic resampling. The implementation is considered aligned only when these tests pass without adding unplanned behavior.
