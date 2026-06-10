# Demo seed data + hosted demo config

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Create `seed-demo.sql` with ~25 synthetic users across 8 archetypes so every MCP tool returns meaningful results in demo mode:

| Archetype | Count |
|-----------|-------|
| Powerlifting-leaning | 4 |
| Bodybuilding-leaning | 4 |
| Cardio / general fitness | 3 |
| Commitment gap | 4 |
| Trial going quiet | 3 |
| Active power user | 3 |
| Coach ignored | 2 |
| Stuck parse | 2 |

Each user needs: profile fields (goals, commitment, experience, coach), 3–10 workouts with realistic `raw_text`, AI chat usage rows, and lifecycle/coach events where relevant.

Wire baked-in demo Supabase URL and service role key into demo mode config. Document setup in README: run migration + seed against the hosted demo project.

## Acceptance criteria

- [ ] `seed-demo.sql` is idempotent or documents clean re-seed procedure
- [ ] All 8 archetypes represented with data exercising every v1 tool
- [ ] Demo mode works out of the box with baked-in creds (no prod secrets)
- [ ] README documents how to apply seed to demo Supabase
- [ ] Manual verification: each tool returns non-empty meaningful results against seeded demo

## Blocked by

- [01-mcp-server-foundation](./01-mcp-server-foundation.md)

## Type

HITL — requires manual application of migration + seed via Supabase SQL Editor on the hosted demo project

## User stories

10, 19
