-- Rep AI Insights MCP — demo database schema
-- =========================================================================
-- Self-contained DDL for a hosted DEMO Supabase project. It mirrors the
-- shape of the production Rep AI tables that the MCP server queries, but
-- WITHOUT the auth.users dependency, RLS, or app-only columns — so a fresh
-- Supabase project can be stood up and seeded in two SQL Editor runs:
--
--   1. Run this file (demo-schema.sql)
--   2. Run seed-demo.sql
--
-- The MCP query paths are identical to production; only the storage backing
-- profiles.id differs (plain uuid here vs auth.users FK in production).
-- Contains only synthetic data — safe to commit credentials for this project.

create extension if not exists pgcrypto;

-- Profiles ----------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  user_tag text not null unique,
  display_name text,
  bio text,
  goals text[],
  commitment text[],
  commitment_frequency text,
  experience_level text,
  coach text,
  gender text,
  age integer,
  height_cm numeric,
  weight_kg numeric,
  trial_start_date timestamptz,
  is_guest boolean not null default false,
  overall_strength_score integer,
  overall_strength_level text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Keep the demo schema safe to re-run against partially-created projects.
-- `create table if not exists` will not add columns to an existing table.
alter table public.profiles
  add column if not exists user_tag text,
  add column if not exists display_name text,
  add column if not exists bio text,
  add column if not exists goals text[],
  add column if not exists commitment text[],
  add column if not exists commitment_frequency text,
  add column if not exists experience_level text,
  add column if not exists coach text,
  add column if not exists gender text,
  add column if not exists age integer,
  add column if not exists height_cm numeric,
  add column if not exists weight_kg numeric,
  add column if not exists trial_start_date timestamptz,
  add column if not exists is_guest boolean not null default false,
  add column if not exists overall_strength_score integer,
  add column if not exists overall_strength_level text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

-- Exercises catalog -------------------------------------------------------
create table if not exists public.exercises (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  muscle_group text,
  type text,
  equipment text,
  aliases text[] default '{}',
  created_at timestamptz not null default now()
);
alter table public.exercises
  add column if not exists name text,
  add column if not exists muscle_group text,
  add column if not exists type text,
  add column if not exists equipment text,
  add column if not exists aliases text[] default '{}',
  add column if not exists created_at timestamptz not null default now();
alter table public.exercises
  alter column id set default gen_random_uuid();
create unique index if not exists idx_exercises_name_unique
  on public.exercises(name);

-- Workout sessions --------------------------------------------------------
create table if not exists public.workout_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  date timestamptz not null default now(),
  raw_text text,
  duration integer,
  notes text,
  type text,
  is_processing boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.workout_sessions
  add column if not exists user_id uuid,
  add column if not exists date timestamptz not null default now(),
  add column if not exists raw_text text,
  add column if not exists duration integer,
  add column if not exists notes text,
  add column if not exists type text,
  add column if not exists is_processing boolean not null default false,
  add column if not exists created_at timestamptz not null default now();
alter table public.workout_sessions
  alter column id set default gen_random_uuid();

create index if not exists idx_workout_sessions_user_id
  on public.workout_sessions(user_id);
create index if not exists idx_workout_sessions_date
  on public.workout_sessions(date);
create index if not exists idx_workout_sessions_processing
  on public.workout_sessions(is_processing, created_at desc);

create table if not exists public.workout_exercises (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.workout_sessions(id) on delete cascade,
  exercise_id uuid not null references public.exercises(id) on delete cascade,
  order_index integer not null,
  notes text,
  created_at timestamptz not null default now()
);
alter table public.workout_exercises
  add column if not exists session_id uuid,
  add column if not exists exercise_id uuid,
  add column if not exists order_index integer,
  add column if not exists notes text,
  add column if not exists created_at timestamptz not null default now();
alter table public.workout_exercises
  alter column id set default gen_random_uuid();
create index if not exists idx_workout_exercises_session
  on public.workout_exercises(session_id);

create table if not exists public.sets (
  id uuid primary key default gen_random_uuid(),
  workout_exercise_id uuid not null
    references public.workout_exercises(id) on delete cascade,
  set_number integer not null,
  reps integer,
  weight numeric,
  rpe numeric,
  rest_time integer,
  notes text,
  created_at timestamptz not null default now()
);
alter table public.sets
  add column if not exists workout_exercise_id uuid,
  add column if not exists set_number integer,
  add column if not exists reps integer,
  add column if not exists weight numeric,
  add column if not exists rpe numeric,
  add column if not exists rest_time integer,
  add column if not exists notes text,
  add column if not exists created_at timestamptz not null default now();
alter table public.sets
  alter column id set default gen_random_uuid();
create index if not exists idx_sets_workout_exercise
  on public.sets(workout_exercise_id);

-- AI chat usage (rate-limit counter; proxy for coach chat volume) ---------
create table if not exists public.ai_chat_usage (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  weight smallint not null default 1,
  created_at timestamptz not null default now()
);
alter table public.ai_chat_usage
  add column if not exists user_id uuid,
  add column if not exists weight smallint not null default 1,
  add column if not exists created_at timestamptz not null default now();
create index if not exists idx_ai_chat_usage_user_created
  on public.ai_chat_usage(user_id, created_at desc);

-- Proactive coach messages ------------------------------------------------
create table if not exists public.proactive_coach_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  trigger_type text not null,
  coach_id text not null,
  body text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  consumed_at timestamptz
);
alter table public.proactive_coach_messages
  add column if not exists user_id uuid,
  add column if not exists trigger_type text,
  add column if not exists coach_id text,
  add column if not exists body text,
  add column if not exists metadata jsonb not null default '{}'::jsonb,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists consumed_at timestamptz;
alter table public.proactive_coach_messages
  alter column id set default gen_random_uuid();
create index if not exists idx_proactive_coach_user_created
  on public.proactive_coach_messages(user_id, created_at desc);

-- Lifecycle email events --------------------------------------------------
create table if not exists public.email_automation_events (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  source_event_id text not null,
  email_type text not null,
  user_id uuid references public.profiles(id) on delete set null,
  recipient_email text not null,
  status text not null default 'sent',
  reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.email_automation_events
  add column if not exists source text,
  add column if not exists source_event_id text,
  add column if not exists email_type text,
  add column if not exists user_id uuid,
  add column if not exists recipient_email text,
  add column if not exists status text not null default 'sent',
  add column if not exists reason text,
  add column if not exists metadata jsonb not null default '{}'::jsonb,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();
alter table public.email_automation_events
  alter column id set default gen_random_uuid();
create index if not exists idx_email_events_user_created
  on public.email_automation_events(user_id, created_at desc);

-- Onboarding strength snapshots -------------------------------------------
create table if not exists public.onboarding_strength_snapshots (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  exercise_id uuid references public.exercises(id) on delete set null,
  working_weight_kg numeric not null,
  reps integer not null,
  estimated_1rm_kg numeric not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.onboarding_strength_snapshots
  add column if not exists exercise_id uuid,
  add column if not exists working_weight_kg numeric,
  add column if not exists reps integer,
  add column if not exists estimated_1rm_kg numeric,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

-- Operator notes (written by the MCP create_ops_note tool) ----------------
create table if not exists public.ops_notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  note text not null check (length(trim(note)) > 0),
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);
alter table public.ops_notes
  add column if not exists user_id uuid,
  add column if not exists note text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists metadata jsonb not null default '{}'::jsonb;
alter table public.ops_notes
  alter column id set default gen_random_uuid();
create index if not exists idx_ops_notes_user_created
  on public.ops_notes(user_id, created_at desc);
