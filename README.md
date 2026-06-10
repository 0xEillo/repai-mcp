# Rep AI Insights MCP

MCP server for understanding and operating [Rep AI](https://repaifit.app) — a live AI workout tracker.

Connects to the Rep AI Supabase backend and exposes safe, read-mostly tools for founder-level questions: who are my users, how do they train, who is going quiet, and is anything failing.

See [docs/PRD.md](docs/PRD.md) for the full product definition and [docs/issues/](docs/issues/) for the implementation plan.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.12 is fetched automatically)
- Docker (optional, for containerized runs)
- An OpenRouter API key (only for LLM-powered tools)

## Setup

```bash
cp .env.example .env   # then fill in values
uv sync
```

### Modes

| Mode | Backend | Credentials |
|------|---------|-------------|
| `demo` | Standalone demo Supabase, synthetic seed data | `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` required unless baked in |
| `prod` | Your Rep AI Supabase project | `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` required |

The service role key is used server-side only and never exposed to MCP clients.

### Demo Supabase setup

The demo project is a self-contained Supabase project holding only synthetic
data. To stand one up:

1. Create a new Supabase project (free tier is fine). Use a blank project, not
   a branch of the production app schema.
2. In the SQL Editor, run [`supabase/demo-schema.sql`](supabase/demo-schema.sql).
3. Then run [`supabase/seed-demo.sql`](supabase/seed-demo.sql) — idempotent,
   safe to re-run (it clears and reseeds the demo uuid namespace).
4. Copy the project URL and key into your local `.env` as `SUPABASE_URL` and
   `SUPABASE_SERVICE_ROLE_KEY`.

The demo schema mirrors the shape of the production Rep AI tables that the MCP
queries use, minus the `auth.users` dependency and RLS, so query paths are
identical to prod. The seed creates ~25 synthetic users across 8 archetypes
(powerlifters, bodybuilders, cardio, commitment gaps, quiet trial users,
power users, coach-ignored, stuck parses) so every tool returns meaningful
results.

Do not run the demo schema or seed against the production project or a Supabase
branch of production. For prod-like databases, apply only
[`supabase/migrations/20260610140000_add_ops_notes.sql`](supabase/migrations/20260610140000_add_ops_notes.sql).

To validate the SQL locally against an ephemeral Postgres:

```bash
uv run --with pgserver --with "psycopg[binary]" python scripts/validate_demo_sql.py
```

## Run

```bash
uv run repai-mcp
```

The server speaks MCP over stdio. Wire it into Cursor / Claude Desktop:

```json
{
  "mcpServers": {
    "repai": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/repai-mcp", "repai-mcp"]
    }
  }
}
```

### Docker

```bash
docker build -t repai-mcp .
docker run -i --env-file .env repai-mcp
```

As an MCP client entry:

```json
{
  "mcpServers": {
    "repai": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--env-file", "/path/to/.env", "repai-mcp"]
    }
  }
}
```

## Tools

| Tool | Status |
|------|--------|
| `health_check` — mode, Supabase reachability, OpenRouter configured | ✅ |
| `investigate_user` — full per-user digest + behavioural signals (LLM persona when configured) | ✅ |
| `describe_user_base` — cohort behavioural aggregates (LLM synthesis when configured) | ✅ |
| `sample_workout_inputs` — filtered samples of raw workout text with context | ✅ |
| `find_commitment_gaps` — stated weekly commitment vs actual frequency | ✅ |
| `find_trial_dropoff_risk` — trial users who have gone quiet | ✅ |
| `find_stuck_workout_sessions` — parses stuck in processing | ✅ |
| `summarize_coach_engagement` — proactive coach sent vs consumed | ✅ |
| `create_ops_note` — log an internal operator note on a user | ✅ |

LLM-powered fields (`investigate_user.persona`, `describe_user_base.synthesis`)
require `OPENROUTER_API_KEY`. Without it both tools degrade gracefully: they
return the structured signals plus an `llm_note` explaining synthesis is
disabled. The model defaults to a Gemini Flash class model and is overridable via
`OPENROUTER_MODEL`.

Every tool call is appended to a local JSONL audit log (`~/.repai-mcp/audit.jsonl` by default, `REPAI_MCP_AUDIT_PATH` to override).

### Prompts

Two MCP prompts guide multi-step agent workflows:

| Prompt | Purpose |
|--------|---------|
| `investigate-quiet-user` (`user_tag`) | Diagnose why a user went quiet: chains `investigate_user` with retention signals |
| `understand-user-base` | Characterise the user base: chains `describe_user_base` with `sample_workout_inputs` |

See [DEMO.md](DEMO.md) for five end-to-end demo flows and a Docker MCP client config.

## Tests

```bash
uv run pytest
```
