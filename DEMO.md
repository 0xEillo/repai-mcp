# Rep AI Insights MCP — Demo

Five end-to-end flows that exercise every v1 tool against the seeded demo
Supabase project. User tags below come from [`supabase/seed-demo.sql`](supabase/seed-demo.sql)
(~25 synthetic users across 8 archetypes).

> Prerequisite: stand up and seed the demo project (see the README
> [Demo Supabase setup](README.md#demo-supabase-setup)). All tool calls are
> appended to the JSONL audit log.

## MCP client config

Wire the server into Cursor / Claude Desktop via Docker:

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

`.env` (copy from [`.env.example`](.env.example)):

```env
REPAI_MCP_MODE=demo
# OPENROUTER_API_KEY=sk-or-...   # optional: enables persona + cohort synthesis
```

LLM-powered fields (`persona`, `synthesis`) appear only when
`OPENROUTER_API_KEY` is set; without it the tools return structured signals plus
a clear `llm_note`.

## Flows

### 1. "What kinds of gym goers use Rep AI?"

- Prompt: **`understand-user-base`**
- Tool chain: `describe_user_base` → `sample_workout_inputs`
- Expect: cohort aggregates (muscle group mix, top exercises, compound/isolation
  ratio, equipment breakdown, avg reps, goal + experience distributions) and, if
  the key is set, an LLM `synthesis`. Raw samples corroborate the personas.

### 2. "Investigate user `trial_tina` — why might they have gone quiet?"

- Prompt: **`investigate-quiet-user`** with `user_tag=trial_tina`
- Tool chain: `investigate_user` → `find_commitment_gaps` / `find_trial_dropoff_risk`
- Expect: a full digest for `trial_tina` (one workout ~6 days ago, quiet since,
  recent trial start). She surfaces in the trial-dropoff cohort. Optionally log a
  finding with `create_ops_note`.

### 3. "Show me how users describe their workouts"

- Tool: `sample_workout_inputs` (e.g. `limit=15`, optional `user_tag` / date range)
- Expect: realistic `raw_text` samples with session id, user tag, and date —
  from terse (`squat_sara`) to messy parse inputs (`stuck_stan`, `parse_pam`).

### 4. "Who's at risk of dropping off during trial?"

- Tool: `find_trial_dropoff_risk`
- Expect: `trial_tom` (never logged a workout), `trial_theo` (inactive since
  trial start), and `trial_tina` (quiet) ranked by risk.

### 5. "Are workout parses failing?"

- Tool: `find_stuck_workout_sessions`
- Expect: `stuck_stan` and `parse_pam`'s sessions stuck in `is_processing=true`,
  with minutes-stuck and a raw-text preview.

## Other tools

- `find_commitment_gaps` — `busy_ben`, `ghost_gina`, `flaky_fred`, `slipping_sue`
  stated more than they train.
- `summarize_coach_engagement` — overall + per-trigger consumption; `ignored_ivan`
  and `silent_sam` never open coach messages.
- `health_check` — mode, Supabase reachability, OpenRouter configured.
