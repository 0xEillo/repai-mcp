# Implementation issues

Vertical slices for [Rep AI Insights MCP v1](../PRD.md). Work in dependency order.

```
01 Foundation
 ├── 02 Ops notes
 ├── 03 investigate_user
 ├── 04 Retention tools
 ├── 05 Qualitative/cohort (SQL)
 └── 07 Demo seed (HITL)
      03 + 05 → 06 LLM layer
      03 + 04 + 05 + 06 → 08 Prompts + DEMO.md
```

| # | Issue | Type | Blocked by |
|---|-------|------|------------|
| 01 | [MCP server foundation](./01-mcp-server-foundation.md) | AFK | — |
| 02 | [Ops notes + create_ops_note](./02-ops-notes-create-ops-note.md) | AFK | 01 |
| 03 | [investigate_user (SQL)](./03-investigate-user.md) | AFK | 01 |
| 04 | [Retention & ops read tools](./04-retention-ops-read-tools.md) | AFK | 01 |
| 05 | [Qualitative + cohort SQL tools](./05-qualitative-cohort-sql-tools.md) | AFK | 01 |
| 06 | [LLM persona layer](./06-llm-persona-layer.md) | AFK | 03, 05 |
| 07 | [Demo seed data](./07-demo-seed-data.md) | HITL | 01 |
| 08 | [MCP prompts + DEMO.md](./08-mcp-prompts-and-demo-md.md) | AFK | 03, 04, 05, 06 |
