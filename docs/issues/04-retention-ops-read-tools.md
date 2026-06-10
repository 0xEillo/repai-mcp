# Retention & ops read tools

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Implement four read-only founder-question tools, each returning typed Pydantic output:

1. **`find_commitment_gaps`** — users whose stated `commitment_frequency` exceeds actual workouts in a configurable lookback window
2. **`find_trial_dropoff_risk`** — users with recent `trial_start_date` and low/no workout activity since
3. **`find_stuck_workout_sessions`** — sessions where `is_processing=true` older than a threshold
4. **`summarize_coach_engagement`** — proactive coach messages sent vs `consumed_at`, aggregate and/or per-user breakdown

All four share the same Supabase query + tool handler patterns established in the foundation slice.

## Acceptance criteria

- [ ] All four tools registered and callable via MCP
- [ ] Each tool returns structured, filterable results (not raw SQL dumps)
- [ ] Sensible defaults for lookback windows and thresholds; overridable via tool inputs
- [ ] Unit tests per tool with mocked Supabase fixtures
- [ ] All tool calls audit-logged

## Blocked by

- [01-mcp-server-foundation](./01-mcp-server-foundation.md)

## Type

AFK

## User stories

4, 5, 6, 7, 21
