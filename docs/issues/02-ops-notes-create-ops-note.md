# Ops notes schema + create_ops_note

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Add the `ops_notes` table migration and wire the `create_ops_note` write tool end-to-end.

Migration SQL must live in both the repai-mcp repo and the Rep AI (uplyft) app repo. The tool accepts a user identifier and note text, validates the user exists, inserts a row, and returns confirmation with the new note id.

Schema shape (from PRD):

```sql
ops_notes (
  id          uuid primary key,
  user_id     uuid references auth.users,
  note        text not null,
  created_at  timestamptz default now(),
  metadata    jsonb default '{}'
)
```

Migrations are applied manually via Supabase SQL Editor — document this in the migration file header.

## Acceptance criteria

- [ ] Migration SQL exists in repai-mcp and uplyft repos
- [ ] `create_ops_note` tool inserts a note and returns structured confirmation
- [ ] Tool rejects unknown user ids with a clear error
- [ ] Tool call is audit-logged
- [ ] Unit tests with mocked Supabase cover success and not-found cases

## Blocked by

- [01-mcp-server-foundation](./01-mcp-server-foundation.md)

## Type

AFK

## User stories

8, 18
