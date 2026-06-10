-- Internal operator notes created by the Rep AI Insights MCP (repai-mcp).
-- Written via the create_ops_note tool using the service role. Not exposed to
-- the mobile app; RLS is enabled so only the service role can read/write.
--
-- Apply manually in the Supabase SQL Editor (production + demo projects).
-- This file is mirrored in the repai-mcp repo.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.ops_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  note TEXT NOT NULL CHECK (length(trim(note)) > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ops_notes_user_created
  ON public.ops_notes(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ops_notes_created
  ON public.ops_notes(created_at DESC);

-- RLS on with no policies: only the service role (used by the MCP server)
-- can access these rows. App clients have no access.
ALTER TABLE public.ops_notes ENABLE ROW LEVEL SECURITY;
