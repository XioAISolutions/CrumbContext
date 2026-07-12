# OpenAI Responses adapter

CrumbContext can run the same-task counterfactual against the OpenAI Responses API while preserving role hierarchy and exact-value guarantees.

```bash
export OPENAI_API_KEY="..."

crumbcontext counterfactual \
  --provider openai \
  --model gpt-5.6 \
  --out openai-proof \
  --open
```

This makes two paid requests: the uncompressed baseline and the routed CrumbContext payload.

## Safety contract

The adapter preserves the provider-native roles supported by Responses:

- `system` remains `system`;
- `developer` remains `developer`;
- `user` remains `user`;
- `assistant` remains `assistant`;
- an unknown non-authoritative source is labelled and mapped to `user` data;
- an unknown authoritative role is rejected instead of silently downgraded.

Assistant `phase` metadata is preserved when a block provides `commentary` or `final_answer`.

Exact-anchor sidecars are reduced to literal values and sent as `input_text`. Paths, hashes, URLs, dates, prices, IDs, and environment variables never depend on image recognition.

## Historical images

Only eligible historical `user` or `tool` blocks can become `input_image` content. Before transmission the adapter:

1. confines the path to the generated routed-artifact directory;
2. verifies that the artifact exists;
3. verifies its SHA-256 when one is present;
4. accepts only PNG, JPEG, WebP, or non-animated GIF;
5. embeds the image as a Base64 data URL;
6. labels it non-authoritative;
7. keeps exact values in native-text sidecars.

The adapter enforces OpenAI's documented 1,500-image and 512 MB total image-payload limits. CrumbContext-generated pages are normally PNG and far below those limits.

Use `--no-images` for a fully text-based comparison. Use `--image-detail low|high|auto|original` to control Responses image detail; CrumbContext defaults to `high` for text-heavy historical pages.

## Prompt caching

OpenAI prompt caching is automatic for eligible requests. CrumbContext supplies a stable `prompt_cache_key` and, on GPT-5.6-or-later model families, marks the final cache-lane text block with an explicit breakpoint while leaving the request-wide mode `implicit`.

```bash
crumbcontext counterfactual \
  --provider openai \
  --prompt-cache-key tenant:acme:project-alpha \
  --out openai-proof
```

The raw cache key is never written to reports. CrumbContext records only its SHA-256.

`--no-cache` disables CrumbContext's cache key and explicit breakpoints. On GPT-5.6-or-later models it uses explicit mode with no breakpoints, which disables prompt caching for that request. Earlier OpenAI models can still apply their provider-managed automatic caching behavior.

Provider-reported usage is normalized into:

- total input tokens;
- uncached input tokens;
- cached input tokens;
- cache-write tokens when reported;
- output tokens;
- reasoning tokens when reported;
- latency;
- response and request IDs;
- request-body SHA-256.

## Privacy and retention

The adapter always sends `store: false`, so the generated response is not stored for later retrieval through the Responses API. This setting is not the same as Zero Data Retention and does not replace your organization's OpenAI data-retention configuration.

CrumbContext never writes `OPENAI_API_KEY` to the provider-neutral request, response record, HTML report, share card, or counterfactual JSON.

## Reproducible claims

A provider run can support a claim only when the published evidence includes:

- model name and dated model snapshot when available;
- fixture or fixture hash;
- task hash;
- baseline and routed request hashes;
- provider-reported usage;
- exact-value recall;
- required-rule recall;
- JSON or structured-output validity;
- response similarity or an external quality evaluation;
- latency;
- routing plan;
- image detail and caching configuration.

One synthetic run is evidence about that run, not a universal savings claim.

## Testing

CI does not make paid requests and needs no OpenAI secret. The adapter accepts an injected HTTP transport so tests cover:

- native role preservation;
- assistant phase preservation;
- exact sidecars;
- path and SHA validation;
- image data URLs and detail settings;
- explicit cache breakpoints;
- provider usage normalization;
- request IDs and API errors;
- missing credentials;
- full baseline-versus-routed counterfactual execution.

Current OpenAI references:

- Responses API: <https://developers.openai.com/api/reference/resources/responses/methods/create>
- Images and vision: <https://developers.openai.com/api/docs/guides/images-vision>
- Prompt caching: <https://developers.openai.com/api/docs/guides/prompt-caching>
