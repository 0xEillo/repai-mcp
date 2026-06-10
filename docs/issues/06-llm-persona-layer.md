# LLM persona layer (OpenRouter BYOK)

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Add OpenRouter integration (BYOK via `OPENROUTER_API_KEY`) and enhance two existing tools with LLM synthesis:

1. **`investigate_user`** — after computing behavioural signals, call LLM to classify training persona (e.g. powerlifting-leaning, bodybuilding-leaning, cardio-focused, general fitness) with confidence and transparent signal attribution.

2. **`describe_user_base`** — after SQL cohort aggregation, make a **single** LLM call to synthesize "what kinds of gym goers use Rep AI?"

Graceful degradation: when `OPENROUTER_API_KEY` is unset, both tools return raw behavioural signals plus a clear message that LLM synthesis is disabled. Use Gemini Flash class model aligned with Rep AI production.

## Acceptance criteria

- [ ] OpenRouter client module with configurable model
- [ ] `investigate_user` includes LLM persona when key is present
- [ ] `describe_user_base` includes LLM cohort synthesis when key is present
- [ ] Both tools degrade gracefully without key — no errors, signals still returned
- [ ] Unit tests mock OpenRouter responses; no real LLM calls in CI
- [ ] Tool calls audit-logged (including whether LLM was invoked)

## Blocked by

- [03-investigate-user](./03-investigate-user.md)
- [05-qualitative-cohort-sql-tools](./05-qualitative-cohort-sql-tools.md)

## Type

AFK

## User stories

2, 14, 15, 16
