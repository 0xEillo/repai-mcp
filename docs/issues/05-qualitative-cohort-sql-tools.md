# sample_workout_inputs + describe_user_base (SQL only)

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Implement two qualitative/cohort tools without LLM:

1. **`sample_workout_inputs`** — return filtered samples of `workout_sessions.raw_text` with metadata (user tag, date, session id). Support filters such as date range, limit, and optional user tag.

2. **`describe_user_base`** — SQL aggregation across all active users: muscle group distribution, top exercises, compound/isolation ratio, equipment breakdown, average reps, goal distribution, experience level breakdown. Return structured signals only — no LLM synthesis yet.

Extract shared signal-computation logic into a reusable module consumed by this slice and later by the LLM persona slice.

## Acceptance criteria

- [ ] `sample_workout_inputs` returns realistic text samples with context metadata
- [ ] `describe_user_base` returns cohort-level behavioural aggregates
- [ ] Shared signal computation module is used by both tools (and ready for issue 06)
- [ ] Unit tests cover aggregation logic with static fixture rows
- [ ] Tool calls audit-logged

## Blocked by

- [01-mcp-server-foundation](./01-mcp-server-foundation.md)

## Type

AFK

## User stories

2 (partial), 3
