# Provider-measured benchmarks

CrumbContext includes a guarded GitHub Actions workflow for generating provider-reported baseline-versus-routed evidence from the bundled public fixture.

The workflow is manual by design. Real provider calls cost money and require account-owned API keys. Pull requests and normal CI never make paid calls.

## One-time environment setup

Create a GitHub environment named exactly:

```text
provider-benchmarks
```

Add only the provider secrets you intend to use:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

Recommended environment controls:

- require a maintainer approval before deployment;
- limit deployment branches to `main`;
- keep API keys scoped to the minimum provider permissions and budget;
- rotate a key immediately if GitHub reports exposure.

Never paste provider keys into workflow inputs, issues, pull requests, logs, fixture files, or benchmark artifacts.

## Run a benchmark

Open **Actions → Provider benchmark → Run workflow** and provide:

| Input | Meaning |
|---|---|
| `provider` | `anthropic` or `openai` |
| `model` | Exact provider model identifier used for the run |
| `profile` | Named routing policy recorded in the evidence bundle |
| `no_images` | Explicitly disable images in addition to the selected profile |
| `recent_turns` | Explicit recent-turn override recorded in the resolved config |
| `redact_responses` | Omit provider response bodies from saved JSON and HTML; defaults to true |
| `run_label` | Filesystem-safe evidence label |

The workflow always uses the repository's bundled public counterfactual fixture. It does not accept arbitrary private transcripts.

Recommended first runs for each provider:

1. `safe-default`, images allowed, response redaction enabled;
2. `text-only`, response redaction enabled.

Do not compare results that use different models, fixtures, tasks, cache settings, or routing profiles as though only the image policy changed.

## What the workflow proves

The same task runs twice:

1. against the complete baseline context;
2. against the CrumbContext-routed payload.

The workflow then requires:

- provider-reported rather than mock-simulated usage;
- a supported explicit counterfactual evidence schema;
- a versioned routing plan containing the named profile and full resolved config;
- successful task completion;
- 100% routed exact-value recall;
- 100% required-rule recall;
- valid task, source, request, and response SHA-256 values;
- non-negative provider token accounting;
- no API-key bytes in generated artifacts.

It records:

- evidence and routing-plan schema versions;
- requested and provider-reported model identifiers;
- task and source SHA-256 hashes;
- baseline and routed request and response hashes;
- routing profile and complete resolved configuration;
- image and cache policy;
- provider usage kind;
- input/output/cache token details returned by the provider;
- latency;
- exact and required-rule recall;
- JSON validity and task completion;
- response similarity;
- whether saved response bodies were redacted;
- the full routing plan;
- baseline and routed request bodies.

Provider response bodies are included only when `redact_responses` is false.

## Artifact handling

The generated `provider-proof/` directory is retained as a private GitHub Actions artifact for 90 days.

Review it before publishing anything. Provider responses can contain generated text that should still be treated as untrusted content.

Response redaction removes provider text from saved JSON and HTML after evaluation. It does not remove:

- task or request content;
- exact sidecars;
- routed image, CRUMB, or summary artifacts;
- hashes, usage, routing config, or evaluation.

Treat the full artifact as sensitive even with response redaction enabled.

The workflow scans all generated files for the configured API-key byte sequences before upload. That is a backstop, not permission to put secrets into prompts.

## Publishing a result

A credible result must state at least:

```text
evidence schema
provider
requested model
provider-reported model
fixture name and source hash
task hash
baseline request hash
routed request hash
routing profile
complete resolved routing configuration
image enabled or text only
cache enabled or disabled
response bodies redacted or retained
baseline and routed token accounting
latency
exact recall
required-rule recall
task completion
response similarity
```

Use precise language:

- **Correct:** “On fixture X with model Y and profile Z, routed input usage was A versus B provider-reported tokens, with 100% exact recall.”
- **Incorrect:** “CrumbContext always cuts AI costs by N%.”

One fixture is evidence for that fixture, model, provider, and policy. It is not a universal billing claim.

## Local equivalent

Anthropic:

```bash
export ANTHROPIC_API_KEY='...'
crumbcontext counterfactual \
  --provider anthropic \
  --model EXACT_MODEL_ID \
  --profile safe-default \
  --redact-responses \
  --out anthropic-proof
```

OpenAI:

```bash
export OPENAI_API_KEY='...'
crumbcontext counterfactual \
  --provider openai \
  --model EXACT_MODEL_ID \
  --profile safe-default \
  --redact-responses \
  --out openai-proof
```

For text-only routing use `--profile text-only`. Keep the full output directory with the published result so hashes, resolved policy, and evaluation remain independently inspectable.

See [ROUTING_PROFILES.md](ROUTING_PROFILES.md) for the profile and schema contract.
