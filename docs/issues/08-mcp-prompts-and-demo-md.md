# MCP prompts + DEMO.md

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Add two MCP prompts that guide multi-step agent workflows:

1. **`investigate-quiet-user`** — chains `investigate_user`, retention signals, and interpretation guidance for "why did this user go quiet?"
2. **`understand-user-base`** — chains `describe_user_base`, `sample_workout_inputs`, and interpretation guidance for cohort understanding

Write `DEMO.md` with five end-to-end demo flows and a Cursor MCP config snippet (`docker run -i` + env file). Cross-link from README.

Demo flows (from PRD):

1. "What kinds of gym goers use Rep AI?" → `describe_user_base`
2. "Investigate user `{demo_user_tag}` — why might they have gone quiet?" → `investigate_user`
3. "Show me how users describe their workouts" → `sample_workout_inputs`
4. "Who's at risk of dropping off during trial?" → `find_trial_dropoff_risk`
5. "Are workout parses failing?" → `find_stuck_workout_sessions`

## Acceptance criteria

- [ ] Both MCP prompts registered and discoverable by MCP clients
- [ ] `DEMO.md` includes all five demo flows with expected tool chains
- [ ] Cursor/Claude Desktop config example included
- [ ] README links to DEMO.md and documents prompt usage
- [ ] Demo flows reference concrete user tags from seed data (issue 07)

## Blocked by

- [03-investigate-user](./03-investigate-user.md)
- [04-retention-ops-read-tools](./04-retention-ops-read-tools.md)
- [05-qualitative-cohort-sql-tools](./05-qualitative-cohort-sql-tools.md)
- [06-llm-persona-layer](./06-llm-persona-layer.md)

## Type

AFK

## User stories

11, 17
