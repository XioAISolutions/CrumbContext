# CrumbContext roadmap

CrumbContext `0.1.0` established the safety contract, deterministic router, inspectable artifacts, same-request counterfactual harness, and Anthropic/OpenAI adapters.

The next phase is not “more compression.” It is stronger evidence, easier integration, and safer operation on real agent workloads.

## v0.2 — Measured and integrable

### 1. Provider-measured evidence suite

- Run the bundled public fixture against at least one exact Anthropic model identifier and one exact OpenAI model identifier.
- Publish baseline and routed request hashes, provider usage, latency, exact recall, task completion, and response similarity.
- Add multiple public fixtures representing coding, research, operations, and tool-heavy agent sessions.
- Keep results fixture-specific; never turn one measurement into a universal savings claim.

### 2. Async and streaming provider execution

- Add async provider interfaces without changing the synchronous API.
- Capture streamed output safely and deterministically.
- Preserve usage, stop reasons, request IDs, and cache accounting when providers report them after streaming completes.
- Test cancellation, timeout, partial response, and retry behavior.

### 3. Stable integration API

- Define a small public Python API for routing blocks and building provider-ready requests.
- Add typed examples for direct Anthropic and OpenAI SDK integration.
- Keep framework-specific adapters thin and optional.
- Avoid making CrumbContext depend on a single agent framework.

### 4. Policy profiles

- Add named routing profiles such as `safe-default`, `text-only`, `cache-heavy`, and `strict-exact`.
- Make every profile resolve to an explicit `RouterConfig` recorded in the plan.
- Support project-local configuration without hidden global state.
- Reject unknown or unsafe policy values.

### 5. Evidence and privacy hardening

- Add artifact retention guidance and configurable response-body redaction.
- Add a machine-readable evidence manifest for provider runs.
- Add schema versioning for routing plans and counterfactual reports.
- Add compatibility checks so old evidence remains readable after new releases.

## v0.3 — Workload evaluation

- Build a versioned public fixture corpus with licensing and provenance metadata.
- Add repeated-run variance reporting for non-deterministic providers.
- Separate routing quality, answer quality, latency, and cost into independent measures.
- Add regression thresholds that fail when exact recall or task completion falls.
- Publish a provider-neutral benchmark protocol others can implement.

## Later, only with evidence

- Framework adapters for widely used agent runtimes.
- Multi-agent shared CRUMB stores.
- Pluggable durable memory backends.
- Incremental routing for very large sessions.
- Policy learning from approved routing decisions.

These are not commitments until they have an issue, acceptance criteria, tests, and a maintainer assigned.

## Non-goals

CrumbContext will not:

- claim that images are universally cheaper than text;
- reconstruct exact values from screenshots;
- flatten system or developer authority into ordinary user content;
- silently upload private transcripts;
- store provider API keys;
- hide routing decisions behind an opaque score;
- publish provider-cost claims without reproducible evidence.

## Definition of done

A roadmap item is complete only when:

1. behavior is documented;
2. tests cover success and failure paths;
3. supported Python versions pass;
4. security-sensitive changes pass CodeQL;
5. generated artifacts remain inspectable;
6. claims match the evidence actually produced.
