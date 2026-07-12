# Contributing

CrumbContext is built around one rule: **lossy optimization must never silently corrupt authority or exact facts**.

## Start

```bash
python -m pip install -e '.[dev]'
pytest
crumbcontext benchmark --out proof
```

## Valuable contributions

- minimal adversarial exact-anchor fixtures;
- routing heuristics with before/after evidence;
- provider adapters that preserve message roles;
- provider-specific counterfactual benchmarks;
- render verification and safe fallbacks;
- clearer proof visualizations.

## Pull request standard

A PR should explain:

1. what context class it changes;
2. what can go wrong;
3. the fallback behavior;
4. tests proving authority and exactness remain intact;
5. whether any claimed reduction is estimated or provider-measured.

Do not add a provider adapter that relocates system/developer content into ordinary user content.
