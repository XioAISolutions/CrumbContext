# CrumbContext roadmap

CrumbContext `0.1.0` established the safety contract, deterministic router, inspectable artifacts, same-request counterfactual harness, and Anthropic/OpenAI adapters.

The next phase is not “more compression.” It is stronger evidence, easier integration, and safer operation on real agent workloads.

## v0.2 — Measured and integrable

### 1. Provider-measured evidence suite — external setup pending

- Run the bundled public fixture against `claude-fable-5` and the existing OpenAI target `gpt-5.6`.
- Publish baseline and routed request hashes, provider usage, latency, exact recall, task completion, and response similarity.
- Keep results fixture-specific; never turn one measurement into a universal savings claim.
- Status: guarded workflows and validators are complete; issues #18 and #19 remain blocked on approved provider keys and budget.

### 2. Async and streaming provider execution — shipped on `main`

- Separate supported `crumbcontext.async_api` surface without changing the synchronous API.
- Normalized Anthropic Messages and OpenAI Responses SSE streams.
- Deterministic mock streams and application-owned transport injection.
- Complete, incomplete, failed, timed-out, cooperative-cancelled, and native-task-cancelled states.
- Partial-result evidence, usage, stop reasons, response IDs, cache accounting, and text redaction.
- Installed-wheel validation on Python 3.10, 3.11, and 3.12.

### 3. Stable integration API — shipped on `main`

- Small public Python API for normalized blocks, baseline/routed requests, provider execution, and native payload dictionaries.
- Typed, keyless examples for Anthropic and OpenAI payload construction.
- No dependency on a single provider SDK or agent framework.
- Installed-wheel compatibility checks across supported Python versions.

### 4. Policy profiles — shipped on `main`

- Named `safe-default`, `text-only`, `cache-heavy`, and `strict-exact` policies.
- Complete resolved `RouterConfig` recorded in every plan.
- Explicit safe overrides without hidden global state.
- Unknown and unsafe policy values fail closed.

### 5. Evidence and privacy hardening — shipped on `main`

- Artifact-retention guidance and configurable response-body redaction.
- Versioned routing, benchmark, counterfactual, provider, stream, workload, and suite schemas.
- Legacy v0.1 document compatibility where schema markers were historically absent.
- Unknown explicit schemas rejected rather than guessed.
- Guarded provider evidence with credential-leak scanning.

### 6. Public multi-workload routing suite — implemented in #31

- Five synthetic CC0 fixtures representing coding, research, operations, tool-heavy, and mixed-authority sessions.
- Four named routing profiles per workload for a 20-run matrix.
- Exact-anchor, authority, recency, image-policy, strict-exact, deterministic-plan, artifact, and lane-coverage checks.
- Manifest and expanded-fixture SHA-256 identity, per-run JSON, aggregate JSON/HTML, and share card.
- Installed-wheel validation on Python 3.10, 3.11, and 3.12.
- Claims remain deterministic planning estimates, not provider billing or model-quality evidence.

## v0.3 — Workload and answer-quality evaluation

- Add repeated-run variance reporting for non-deterministic providers.
- Separate routing quality, answer quality, latency, and cost into independent measures.
- Add task-specific answer-quality graders that do not weaken exact-value or authority checks.
- Expand the public fixture corpus with licensing and provenance review.
- Add regression thresholds that fail when exact recall, required-rule recall, or task completion falls.
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
- publish provider-cost claims without reproducible evidence;
- present offline planning estimates as provider billing or model-quality proof.

## Definition of done

A roadmap item is complete only when:

1. behavior is documented;
2. tests cover success and failure paths;
3. supported Python versions pass;
4. security-sensitive changes pass CodeQL;
5. generated artifacts remain inspectable;
6. claims match the evidence actually produced.
