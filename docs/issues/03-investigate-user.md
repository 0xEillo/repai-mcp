# investigate_user (SQL digest)

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Implement `investigate_user` — a founder-question tool that returns a full structured digest for one user, looked up by `user_tag`.

Include: profile and onboarding intent (goals, commitment, experience, coach), recent workout summary, AI chat usage volume, proactive coach messages (sent/consumed), lifecycle email events, onboarding strength snapshot, and computed training behavioural signals (top exercises, muscle group mix, compound/isolation ratio, equipment breakdown, avg reps).

No LLM in this slice — persona classification comes in issue 06. Output must be a typed Pydantic model suitable for agent reasoning.

## Acceptance criteria

- [ ] `investigate_user(user_tag)` returns complete digest for a known user
- [ ] Unknown `user_tag` returns a clear not-found error
- [ ] Behavioural signals are computed from joined workout/exercise/set data
- [ ] Output schema is documented via Pydantic model fields
- [ ] Unit tests with mocked Supabase fixture data cover a representative user
- [ ] Tool call is audit-logged

## Blocked by

- [01-mcp-server-foundation](./01-mcp-server-foundation.md)

## Type

AFK

## User stories

1 (partial), 20, 21, 22, 23, 24
