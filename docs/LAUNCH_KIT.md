# CrumbContext launch kit

This document is the copy-and-paste launch surface for the standalone repository.

## Repository identity

**Repository name**

```text
CrumbContext
```

**Description**

```text
Safety-first context routing for AI agents. Exact facts stay exact while stale context takes a cheaper lane.
```

**Website**

Use the project documentation or landing page once live. Until then, leave blank rather than pointing to an unrelated company page.

## GitHub topics

Add these in the repository **About** panel:

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

The first eight carry the clearest product meaning. Avoid adding unrelated high-volume topics merely for impressions.

## Social preview

Upload:

```text
docs/assets/social-preview.svg
```

In GitHub: **Settings → General → Social preview → Edit**.

## Hashtags

Use five to eight per post. A wall of tags looks automated.

**Core**

```text
#CrumbContext #ContextEngineering #AIAgents #LLMOps #OpenSource #DeveloperTools
```

**Technical rotation**

```text
#Python #PromptCaching #AgentMemory #TokenOptimization #AIInfrastructure #LocalAI
```

**Tool-community rotation**

```text
#ClaudeCode #OpenAI #Codex #Anthropic #AgenticAI
```

## X / Twitter launch post

```text
AI agents keep resending huge histories as if every token has equal value.

It does not.

System instructions, current requests, hashes, paths, prices and IDs must stay exact. Old logs and stale context can take cheaper lanes.

I built CrumbContext: an open-source, safety-first router that sends context to exact text, cache, CRUMB memory, sanitized images or deterministic summaries.

The bundled offline benchmark self-checks:
• 31/31 exact anchors preserved
• authority and recent turns stay native text
• every routing decision is inspectable

No API key needed:
crumbcontext benchmark --out proof --open

[REPOSITORY LINK]

#CrumbContext #ContextEngineering #AIAgents #LLMOps #OpenSource #Python
```

## LinkedIn launch post

```text
Most AI context systems optimize for one thing: fitting more into the window.

That is not enough.

A system instruction is not the same kind of context as an old tool log. A SHA, file path, price or citation should not be reconstructed from a lossy summary or image.

Today I am releasing CrumbContext, an open-source safety-first context router for AI agents.

It separates context into five explainable lanes:
1. Exact text for authority, current turns and precision-critical facts
2. Cache candidates for stable repeated reference material
3. CRUMB memory for decisions and handoffs
4. Sanitized images for old dense logs
5. Deterministic summaries for stale semantic context

Before any lossy transform, CrumbContext extracts exact anchors into native-text sidecars. The bundled offline benchmark preserves 31/31 exact values and generates a report explaining every routing decision.

This is an alpha and the token figures are planning estimates—not a fake provider-billing claim. The next milestone is a same-request provider counterfactual harness.

Repository: [REPOSITORY LINK]

#CrumbContext #ContextEngineering #AIAgents #AIInfrastructure #OpenSource #DeveloperTools
```

## Hacker News title and first comment

**Title**

```text
Show HN: CrumbContext – Route AI context without turning exact facts into pixels
```

**First comment**

```text
I built this after noticing that context-compression techniques often treat every message as equivalent. They are not: system authority, a current request, an old log and a project-memory handoff have different failure costs.

CrumbContext is currently provider-neutral. It extracts paths, hashes, IDs, URLs, dates and amounts into exact-text sidecars, then routes stale context to cache, CRUMB memory, sanitized images or deterministic summaries. The bundled benchmark is offline and intentionally labels its token counts as estimates.

The part I would most value feedback on is the routing policy and adversarial exact-anchor fixtures. I do not want to rush a transparent proxy until role semantics and safe fallback are proven.
```

## Reddit framing

Use a technical community and lead with the problem, benchmark methodology, and limitations. Do not paste the same promotional copy into multiple communities.

Suggested title:

```text
I open-sourced a context router that keeps exact IDs and instructions out of lossy compression
```

## Product Hunt tagline

```text
Route AI context intelligently—without losing exact facts.
```

## One-line pitches

```text
The safety layer between a long AI conversation and the next model call.
```

```text
Context engineering with five lanes and one hard rule: exact facts stay exact.
```

```text
Stop resending the entire conversation. Route each block based on authority, reuse and precision.
```

## First-week launch sequence

1. Publish the repository with CI green and social preview uploaded.
2. Post the generated benchmark card and a 20–30 second terminal recording.
3. Open three concrete roadmap issues: provider counterfactual harness, Anthropic adapter, OpenAI adapter.
4. Ask for adversarial fixtures rather than generic feedback.
5. Reply publicly with benchmark limitations and fixes; do not defend weak heuristics.
6. Tag the first release only after the clean installation path is proven on a fresh machine.
7. Pin the repository on the organization and maintainer profiles.

## Repository settings checklist

- Enable Issues and Discussions.
- Disable Wikis unless they will be maintained.
- Require pull requests for `main` after the first public push.
- Require the CI workflow before merge.
- Enable Dependabot alerts and security updates.
- Upload `docs/assets/social-preview.svg`.
- Add the topics listed above.
- Create a `v0.1.0` release only after CI passes in the standalone repository.
- Configure the PyPI trusted publisher before publishing the GitHub release.
- Pin `README`, `ARCHITECTURE`, `LAUNCH_KIT`, and the benchmark issue in Discussions or repository navigation where appropriate.

## Claims policy

Safe public language:

```text
The bundled fixture shows a 65.8% deterministic planning reduction while preserving 31/31 exact anchors.
```

Do not say:

```text
CrumbContext cuts every AI bill by 65.8%.
```

Provider-billed savings require a same-request counterfactual with output-quality and exact-recall checks.
