## Problem Statement

Rep AI is a live AI workout tracker with a rich Supabase backend, but operational and product understanding workflows are fragmented. As the founder/operator, understanding users requires manually querying multiple tables, reading raw workout inputs, cross-referencing onboarding intent with actual behaviour, and interpreting training patterns — work that dashboards and Mixpanel cannot easily answer qualitatively.

There is no internal ops layer that lets an AI agent answer founder-level questions like "what kinds of gym goers use my app?", "why did this user go quiet?", or "how do users actually describe their workouts?" in a single structured workflow.

Interactive evaluation also requires a standalone, runnable MCP server — not code buried inside the mobile app repo — with demo data that works without production credentials.

## Solution

Build **Rep AI Insights MCP**: a standalone Python MCP server (stdio + Docker) that connects to the Rep AI Supabase backend and exposes narrowly scoped, founder-question-oriented tools. The server compresses multi-step operational workflows into safe, structured tool calls that an AI agent can chain into actionable answers.

The server supports two modes:
- **Demo mode** — connects to a hosted demo Supabase project with seeded synthetic users; evaluators can clone and run immediately (plus their own OpenRouter key for LLM tools).
- **Prod mode** — connects to the live Rep AI Supabase for daily founder use.

LLM-powered tools use OpenRouter (BYOK) for training persona classification. Cohort analysis uses SQL aggregation + a single LLM synthesis call; per-user investigation uses behavioural signals + one LLM call per user.

## User Stories

1. As a founder, I want to investigate a specific user by tag, so that I can understand their full journey (profile, workouts, AI usage, coach engagement, lifecycle events, training persona) in one call.
2. As a founder, I want to understand what kinds of gym goers use Rep AI, so that I can tailor product decisions to my actual user base (powerlifters, bodybuilders, cardio-focused, general fitness).
3. As a founder, I want to sample raw workout text inputs from users, so that I can understand how people naturally describe workouts and improve parsing/UX.
4. As a founder, I want to find users who committed to a training frequency but aren't hitting it, so that I can identify retention risks early.
5. As a founder, I want to find trial users who are going quiet, so that I can understand trial-to-paid dropoff patterns.
6. As a founder, I want to find stuck workout parse sessions, so that I can debug AI/parsing failures in production.
7. As a founder, I want to summarize proactive coach message engagement, so that I can evaluate whether the coach feature is working.
8. As a founder, I want to create internal notes on users, so that I can record investigation findings alongside user data.
9. As a founder, I want every tool call audited locally, so that I have a record of what the agent queried and when.
10. As an evaluator (InteractiveAI), I want to clone the repo and run the MCP against demo data without production credentials, so that I can verify it works independently.
11. As an evaluator, I want documented demo prompts that exercise the tools, so that I can see a realistic agent workflow end-to-end.
12. As an evaluator, I want Docker packaging with stdio transport, so that I can connect the server to Cursor or Claude Desktop easily.
13. As a founder, I want to switch between demo and prod backends via configuration, so that I use the same codebase for development, demo, and daily ops.
14. As a founder, I want LLM tools to degrade gracefully when no OpenRouter key is set, so that read-only tools still work.
15. As a founder, I want training persona analysis powered by LLM interpretation of behavioural signals, so that classification goes beyond simple SQL aggregates.
16. As a founder, I want cohort persona analysis via a single LLM call over aggregated signals, so that "describe my user base" is fast and affordable.
17. As an agent user, I want MCP prompts that guide multi-step investigation workflows, so that common questions have reusable templates.
18. As a founder, I want the ops notes table migration tracked in both the MCP repo and the app repo, so that schema changes are auditable in the product codebase.
19. As a founder, I want demo seed data covering diverse user archetypes, so that every tool returns meaningful results during evaluation.
20. As a founder, I want the MCP server to use the same Supabase schema as the live app, so that tools reflect real product data structures.
21. As a founder, I want to query user onboarding intent (goals, commitment, experience) alongside actual workout behaviour, so that I can spot intent-behaviour gaps.
22. As a founder, I want to see onboarding strength snapshots alongside later workout data, so that I can understand whether users train as they initially indicated.
23. As a founder, I want to see lifecycle email events for a user, so that I can correlate billing/cancellation signals with activity changes.
24. As a founder, I want to see AI chat usage volume per user, so that I can understand engagement with the coach feature beyond proactive messages.
25. As an agent, I want structured JSON tool outputs with consistent schemas, so that I can reason over results reliably.
26. As a founder, I want the server to run server-side only with service role credentials never exposed to clients, so that database access remains secure.
27. As a developer, I want typed tool inputs/outputs via Pydantic models, so that schemas are self-documenting and testable.
28. As a developer, I want uv for dependency management, so that the project follows modern Python packaging conventions.
29. As an evaluator, I want a `.env.example` documenting all required configuration, so that setup is straightforward.
30. As a founder, I want to run the MCP via Docker with stdio, so that deployment is reproducible across machines.

## Implementation Decisions

### Architecture

- **Standalone repo**: `repai-mcp` — separate from the Rep AI (Uplyft) mobile app monorepo.
- **Language/runtime**: Python 3.12+, managed with `uv`.
- **MCP framework**: FastMCP with Pydantic input/output models per tool.
- **Transport**: stdio (primary); Docker as packaging layer (`docker run -i`).
- **Database client**: Supabase Python client with service role key, server-side only.

### Configuration

```
REPAI_MCP_MODE=demo|prod
SUPABASE_URL              # required in prod; optional override in demo
SUPABASE_SERVICE_ROLE_KEY # required in prod; optional override in demo
OPENROUTER_API_KEY        # BYOK; required for LLM tools
```

- **Demo mode**: baked-in demo Supabase URL and service role key (demo project only, read-only scope).
- **Prod mode**: founder supplies prod credentials via environment variables.
- **Override**: env vars always override baked-in demo creds when set.

### MCP Tools (v1 — locked)

**Read tools (7):**

| Tool | Purpose |
|------|---------|
| `investigate_user` | Full user digest: profile, recent activity, AI usage, coach messages, lifecycle events, onboarding strength + LLM training persona classification |
| `describe_user_base` | Cohort-level "what kinds of gym goers use Rep AI?" — SQL aggregation of behavioural signals + single LLM synthesis call |
| `sample_workout_inputs` | Filtered samples of `workout_sessions.raw_text` for qualitative analysis |
| `find_commitment_gaps` | Users whose stated commitment frequency exceeds actual workout frequency |
| `find_trial_dropoff_risk` | Trial users (`trial_start_date`) with low recent activity |
| `find_stuck_workout_sessions` | Sessions with `is_processing=true` beyond a threshold |
| `summarize_coach_engagement` | Proactive coach messages sent vs `consumed_at` across users or for a cohort |

**Write tool (1):**

| Tool | Purpose |
|------|---------|
| `create_ops_note` | Persist internal investigation note linked to a user |

**MCP Prompts (2):**

| Prompt | Purpose |
|--------|---------|
| `investigate-quiet-user` | Guides agent through user investigation workflow |
| `understand-user-base` | Guides agent through cohort analysis + raw input sampling |

### LLM Integration

- **Provider**: OpenRouter (BYOK via `OPENROUTER_API_KEY`).
- **Model**: Gemini Flash class (cheap, fast — align with Rep AI production model family).
- **Per-user persona** (`investigate_user`): compute behavioural signals in SQL, send to LLM for persona label + interpretation.
- **Cohort persona** (`describe_user_base`): aggregate signals across all users in SQL, single LLM call to synthesize user-base breakdown.
- **Graceful degradation**: if no OpenRouter key, LLM tools return raw behavioural signals with a clear message that LLM synthesis is disabled.

### Training Persona Signals (computed in SQL, interpreted by LLM)

Behavioural signals derived from existing schema — no new persona columns required for v1:

- Top exercises by frequency (join `workout_sessions` → `workout_exercises` → `exercises`)
- Muscle group distribution
- Compound vs isolation ratio (`exercises.type`)
- Equipment breakdown (`exercises.equipment`)
- Average reps/weight/RPE from `sets`
- Stated goals from `profiles.goals`
- Experience level from `profiles.experience_level`
- Onboarding strength snapshot from `onboarding_strength_snapshots`

LLM interprets signals into personas such as powerlifting-leaning, bodybuilding-leaning, cardio-focused, general fitness — with confidence and transparent signal attribution.

### Audit & Notes

- **Audit log**: local append-only JSONL file (e.g. `~/.repai-mcp/audit.jsonl` or `./data/audit.jsonl` in Docker). Logs every tool call: timestamp, tool name, inputs (sanitized), mode, duration.
- **Ops notes**: Supabase table `ops_notes` — persists founder notes linked to user ID.
- **No PII masking for v1**: founder tool with founder DB access; demo uses synthetic data.

### Schema Changes

**New table: `ops_notes`**

Migration SQL lives in both repos (MCP repo + Rep AI app repo). Applied manually via Supabase SQL Editor on demo and prod when ready.

Conceptual shape:

```sql
ops_notes (
  id          uuid primary key,
  user_id     uuid references auth.users,
  note        text not null,
  created_at  timestamptz default now(),
  metadata    jsonb default '{}'
)
```

No other schema changes required for v1. Existing tables used:

- `profiles`, `workout_sessions`, `workout_exercises`, `exercises`, `sets`
- `ai_chat_usage`, `email_automation_events`, `proactive_coach_messages`
- `onboarding_strength_snapshots`, `retention_push_preferences`

Explicitly **not** in DB (accepted gaps): subscription status (RevenueCat), onboarding funnel events (Mixpanel), coach chat transcripts (local MMKV), in-app feedback.

### Demo Supabase

- Hosted demo project with credentials documented in README.
- Seed script (`seed-demo.sql`) with ~25 synthetic users across 8 archetypes:
  - Powerlifting-leaning (4)
  - Bodybuilding-leaning (4)
  - Cardio / general fitness (3)
  - Commitment gap (4)
  - Trial going quiet (3)
  - Active power user (3)
  - Coach ignored (2)
  - Stuck parse (2)
- Each user includes: profile fields, 3–10 workouts with realistic `raw_text`, AI chat usage rows, lifecycle/coach events as relevant.

### Project Structure

```
repai-mcp/
├── pyproject.toml
├── src/repai_mcp/
│   ├── server.py       # FastMCP entrypoint
│   ├── config.py       # mode, creds, paths
│   ├── tools/          # one module per tool
│   ├── supabase/       # client + queries
│   ├── llm/            # OpenRouter client + prompt templates
│   └── audit.py        # JSONL audit logger
├── supabase/
│   ├── migrations/     # ops_notes.sql
│   └── seed-demo.sql
├── Dockerfile
├── .env.example
├── README.md
└── DEMO.md
```

### Docker

- Single-stage or slim multi-stage image with uv.
- Entrypoint: `uv run repai-mcp` over stdio.
- Requires `-i` flag for interactive stdin.
- Env vars injected at runtime via `--env-file`.

## Testing Decisions

### What makes a good test

- Test **external behaviour** of tools: given known Supabase fixture data, tool returns expected structured output.
- Do **not** test implementation details (internal SQL string formatting, LLM prompt wording).
- Mock Supabase client and OpenRouter client at the boundary — do not hit real services in unit tests.
- Integration tests (optional, manual): run against demo Supabase with seed data to verify end-to-end.

### Testing seams (highest seam possible)

1. **Tool handler level** (primary seam): each MCP tool is a function `(supabase_client, config) → Pydantic model`. Test with mocked Supabase responses returning fixture dicts. This is the highest useful seam — tests the full tool contract without MCP transport or real DB.

2. **SQL query module level** (secondary seam): pure functions that build/execute queries and transform rows → signal structs. Test transformation logic with static row fixtures (e.g. given these exercise rows, compute muscle group distribution correctly).

3. **LLM module level**: mock OpenRouter response; verify persona tool returns structured output combining signals + LLM interpretation. Do not call real LLM in CI.

4. **Config module**: test demo/prod mode resolution and env override logic.

5. **Audit module**: test JSONL append writes expected record shape.

6. **End-to-end (manual / demo)**: connect MCP to demo Supabase via Cursor, run DEMO.md prompts. Not automated in v1.

### Modules tested

| Module | Test type |
|--------|-----------|
| Tool handlers | Unit with mocked Supabase + mocked LLM |
| Query/signal computation | Unit with fixture rows |
| Config resolution | Unit |
| Audit logger | Unit |
| LLM response parsing | Unit with mocked responses |

No prior art in repai-mcp (greenfield). Follow standard pytest conventions.

## Out of Scope

- HTTP/SSE MCP transport (stdio only for v1)
- Embedded/rate-limited OpenRouter demo key (BYOK only)
- PII masking (deferred — founder tool, synthetic demo data)
- Supabase audit log table (local JSONL only)
- `ai_generation_events` table / AI failure logging (requires app changes)
- RevenueCat / Mixpanel integration
- Coach chat history (stored locally on device only)
- In-app feedback search (no feedback table)
- Generic natural-language SQL
- Admin dashboard or web UI
- User-facing write operations (delete user, edit workout, change subscription, send push, etc.)
- Multi-tenant auth / permission model beyond service role + mode flag
- Automated migration application (manual SQL Editor only)
- Production deployment / hosting (runs locally or via Docker on operator machine)

## Further Notes

### Demo story for evaluators

> "I built a standalone MCP server for understanding Rep AI users — real Supabase schema, LLM-powered persona analysis, founder-question tools not database getters. Public repo with seeded demo data; I run it against prod daily."

Suggested demo prompts (for DEMO.md):

1. "What kinds of gym goers use Rep AI?" → `describe_user_base`
2. "Investigate user `{demo_user_tag}` — why might they have gone quiet?" → `investigate_user`
3. "Show me how users describe their workouts" → `sample_workout_inputs`
4. "Who's at risk of dropping off during trial?" → `find_trial_dropoff_risk`
5. "Are workout parses failing?" → `find_stuck_workout_sessions`

### Relationship to Rep AI app

- MCP reads the same Supabase schema the app writes to.
- Only schema addition is `ops_notes` — an operational table, not an app feature.
- No changes to edge functions, iOS app, or existing migrations required for v1 (except applying `ops_notes` migration).

### Future v1.1 candidates

- `ai_generation_events` logging in parse-workout edge function
- PII masking for shared-screen demos
- Supabase-backed audit log
- RevenueCat API integration for subscription context
- HTTP transport for remote hosting on InteractiveAI platform
