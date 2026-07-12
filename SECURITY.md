# Security policy

CrumbContext handles prompts, logs, identifiers, generated images, exact-value sidecars, and potentially sensitive project context. Treat inputs and output directories as confidential unless they are deliberately synthetic or redacted.

## Supported versions

| Version | Supported |
|---|---|
| `0.1.x` | Yes |
| pre-release snapshots | Best effort |

## Reporting a vulnerability

Do not place private transcripts, API keys, credentials, proprietary logs, or exploitable details in a public issue.

For security-sensitive reports, contact XIO AI Solutions privately before public disclosure. Include:

- affected version or commit;
- minimal synthetic reproduction;
- impact and likely attack path;
- whether the issue affects local routing, artifact generation, Anthropic mapping, OpenAI mapping, or release infrastructure;
- suggested mitigation when known.

## Data-handling boundaries

- `analyze`, `route`, `demo`, `benchmark`, and the mock counterfactual can run without a provider key.
- Anthropic and OpenAI network calls occur only when the corresponding provider is explicitly selected.
- API keys are read from environment variables or direct constructor arguments and are not written to comparison artifacts.
- OpenAI Responses requests set `store: false`.
- Raw OpenAI prompt-cache keys are not written to reports; only SHA-256 representations are retained.
- Exact-anchor sidecars intentionally contain extracted literal values. This is required for exact recall and means the sidecars are sensitive.
- Generated image pages contain sanitized historical context and can still contain confidential prose.
- Request and response JSON files can contain model outputs and routed context. Protect or delete them according to your project policy.
- The hidden `--api-url` test/development override can redirect provider traffic. Do not use an untrusted endpoint.

## Adapter safety rules

Provider adapters must:

- preserve system/developer authority using provider-native structures;
- preserve user and assistant history without silently raising its authority;
- send exact anchors as native text rather than relying on OCR or vision;
- restrict image routing to eligible non-authoritative historical context;
- confine artifact paths to the routed output directory;
- verify artifact hashes and supported image formats;
- fail closed to exact text or a clear error when role or artifact semantics are uncertain;
- avoid persisting API credentials and raw cache identifiers.

## Current alpha limitations

CrumbContext is not a secret scanner, DLP product, sandbox, or guarantee against prompt injection. Exact-anchor extraction covers documented patterns but cannot identify every sensitive value. Historical images and summaries remain model-visible context and should be treated as untrusted evidence. Users are responsible for securing generated files and deciding which transcripts may be sent to external providers.

Use synthetic or redacted fixtures in public issues, pull requests, benchmark posts, and screenshots.
