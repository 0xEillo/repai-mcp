# MCP server foundation (boot + connect)

## Parent

[PRD: Rep AI Insights MCP v1](../PRD.md)

## What to build

Bootstrap the repai-mcp Python project end-to-end: uv-managed dependencies, FastMCP server with stdio transport, demo/prod configuration, Supabase client factory, and JSONL audit logging wrapped around every tool call.

Deliver a working Docker image and `.env.example`. Include pytest scaffolding. Ship one connectivity tool (e.g. `health_check`) that reports current mode, Supabase reachability, and whether OpenRouter is configured — without calling the LLM.

Every tool invocation must append an audit record (timestamp, tool name, inputs, mode, duration) to the local JSONL audit log.

## Acceptance criteria

- [ ] `uv sync` and `uv run repai-mcp` start the MCP server over stdio
- [ ] `REPAI_MCP_MODE=demo|prod` resolves Supabase creds correctly; env vars override baked-in demo creds
- [ ] Docker image builds and runs with `docker run -i --env-file .env repai-mcp`
- [ ] Connectivity tool returns mode + Supabase connection status
- [ ] Audit log writes one JSONL entry per tool call
- [ ] Unit tests cover config resolution and audit log record shape
- [ ] `.env.example` documents all required variables

## Blocked by

None — can start immediately

## Type

AFK

## User stories

9, 12, 13, 25, 26, 27, 28, 29, 30
