# CrumbContext launch kit

This is the copy-and-paste launch surface for the standalone project. Keep every public claim tied to a reproducible fixture or provider result.

## Repository identity

**Description**

```text
Safety-first context routing for AI agents. Exact facts stay exact while stale context takes a cheaper lane.
```

**Core line**

```text
Give every AI the context it needs—not the entire conversation.
```

**Hard rule**

```text
Exact facts never become pixels.
```

## GitHub topics

Use the most relevant topics first:

```text
ai
llm
ai-agents
context-engineering
context-window
prompt-caching
agent-memory
llmops
token-optimization
developer-tools
python
open-source
local-ai
anthropic
openai
claude-code
codex
prompt-engineering
ai-infrastructure
agentic-ai
```

Do not add unrelated high-volume topics merely for impressions.

## Social preview

Upload `docs/assets/social-preview.svg`, or a 1280×640 PNG export, through:

```text
Settings → General → Social preview → Edit
```

## Hashtags

Use five to eight per post.

**Core**

```text
#CrumbContext #ContextEngineering #AIAgents #LLMOps #OpenSource #DeveloperTools
```

**Technical rotation**

```text
#Python #PromptCaching #AgentMemory #TokenOptimization #AIInfrastructure #LocalAI
```

**Provider/tool rotation**

```text
#Anthropic #OpenAI #ClaudeCode #Codex #AgenticAI
```

## X / Twitter launch post

```text
AI agents keep resending huge histories as if every token has equal value.

It does not.

System instructions, current requests, hashes, paths, prices and IDs must stay exact. Old logs and stale context can take cheaper lanes.

CrumbContext is an open-source, safety-first router that sends context to exact text, provider cache, CRUMB memory, sanitized images, or deterministic summaries.

The bundled offline proof self-checks:
• 31/31 exact anchors preserved
• authority and recent turns stay native text
• every routing decision is inspectable

It also includes same-task counterfactual adapters for Anthropic Messages and OpenAI Responses, with provider usage, latency, hashes, exact recall and task-completion scoring.

No key needed for the offline proof:
crumbcontext benchmark --out proof --open

https://github.com/XioAISolutions/CrumbContext

#CrumbContext #ContextEngineering #AIAgents #LLMOps #OpenSource #Python
```

## LinkedIn launch post

```text
Most AI context systems optimize for fitting more into the window. That is not enough.

A system instruction is not the same kind of context as an old tool log. A SHA, file path, price, URL or citation should not be reconstructed from a lossy summary or image.

CrumbContext is an open-source safety-first context router for AI agents. It separates context into five explainable lanes:

1. Exact text for authority, current turns and precision-critical facts
2. Provider cache candidates for stable repeated references
3. CRUMB memory for decisions and handoffs
4. Sanitized images for old dense logs
5. Deterministic summaries for stale semantic context

Before any lossy transform, exact anchors are extracted into native-text sidecars. The bundled fixture preserves 31/31 exact values and generates a report explaining every routing decision.

The project now includes same-request counterfactual adapters for Anthropic Messages and OpenAI Responses. Real provider runs record usage, cache details when returned, latency, request hashes, exact recall, task completion and response similarity.

The 65.8% bundled result is a deterministic planning estimate for one fixture—not a universal billing claim.

Repository: https://github.com/XioAISolutions/CrumbContext

#CrumbContext #ContextEngineering #AIAgents #AIInfrastructure #OpenSource #DeveloperTools
```

## Hacker News

**Title**

```text
Show HN: CrumbContext – Route AI context without turning exact facts into pixels
```

**First comment**

```text
I built this after noticing that context-compression systems often treat every message as equivalent. They are not: system authority, a current request, an old log and a project-memory handoff have different failure costs.

CrumbContext extracts paths, hashes, IDs, URLs, dates and amounts into exact-text sidecars, then routes stale context to provider cache, CRUMB memory, sanitized images or deterministic summaries.

The repository includes an offline proof plus same-task counterfactual adapters for Anthropic Messages and OpenAI Responses. Provider runs save request hashes, usage, latency and quality checks. The bundled token figure is deliberately labelled as a planning estimate.

The feedback I value most is adversarial fixtures, role-mapping failures and cases where exact-text fallback should trigger earlier.
```

## Reddit framing

Suggested title:

```text
I open-sourced a context router that keeps exact IDs and instructions out of lossy compression
```

Lead with the problem, implementation, benchmark methodology, provider mapping, and limitations. Do not paste identical promotional copy into multiple communities.

## Product Hunt

**Tagline**

```text
Route AI context intelligently—without losing exact facts.
```

**One-liner**

```text
The safety layer between a long AI conversation and the next model call.
```

## Provider-measured result template

Use this structure only after a real provider run:

```text
Provider/model: [EXACT PROVIDER AND MODEL]
Fixture: [PUBLIC OR HASHED FIXTURE]
Baseline request SHA-256: [HASH]
Routed request SHA-256: [HASH]
Input tokens: [BASELINE] → [ROUTED]
Cache details: [PROVIDER-REPORTED VALUES]
Latency: [BASELINE] → [ROUTED]
Exact recall: [FOUND]/[EXPECTED]
Task complete: [TRUE/FALSE]
Response similarity: [VALUE]
Routing policy: [COMMIT OR PLAN HASH]
```

Never publish a percentage without the model, fixture, quality result, and request hashes beside it.

## First-week launch sequence

1. Publish `v0.1.0` only after PyPI trusted publishing is configured.
2. Verify clean installation from PyPI using `docs/RELEASE.md`.
3. Upload the social preview and apply repository topics.
4. Post the offline benchmark card with the planning-estimate disclaimer.
5. Record a short terminal demo: benchmark → report → counterfactual.
6. Run one Anthropic and one OpenAI provider benchmark using the same public fixture.
7. Publish the raw result JSON or a redacted reproducible bundle.
8. Ask for adversarial fixtures and role-preservation failures rather than generic praise.
9. Pin the repository on the organization and maintainer profiles.

## Repository settings checklist

- Add the repository description above.
- Add the recommended topics.
- Upload the social preview.
- Enable Issues and Discussions as desired.
- Disable Wikis unless they will be maintained.
- Require pull requests and CI/CodeQL for `main`.
- Enable Dependabot alerts and security updates.
- Configure the `pypi` environment and trusted publisher.
- Publish `v0.1.0` using `docs/RELEASE_NOTES_v0.1.0.md`.
- Pin the release process and benchmark methodology where contributors can find them.

## Claims policy

Safe offline language:

```text
The bundled fixture shows a 65.8% deterministic planning reduction while preserving 31/31 exact anchors.
```

Safe provider language:

```text
On provider X, model Y and fixture Z, the routed request used N% fewer provider-reported input tokens while preserving all required exact values and passing the published task checks.
```

Do not say:

```text
CrumbContext cuts every AI bill by 65.8%.
```

A single provider run is evidence for that exact run—not a universal guarantee.
