-- Rep AI Insights MCP — demo seed data
-- =========================================================================
-- Idempotent. Re-running deletes prior demo rows (by the demo uuid
-- namespace 11111111-1111-4111-8111-*) and reinserts. Run after
-- demo-schema.sql. Synthetic data only — no real users.
--
-- ~25 users across 8 archetypes so every v1 tool returns meaningful results:
--   powerlifting (4), bodybuilding (4), cardio/general (3),
--   commitment gap (4), trial going quiet (3), active power user (3),
--   coach ignored (2), stuck parse (2).

-- 1) Cleanup ---------------------------------------------------------------
-- Delete demo rows explicitly instead of relying only on FK cascades. This
-- keeps the seed idempotent even if the schema is rerun over partial tables.
delete from public.sets s
using public.workout_exercises we, public.workout_sessions ws
where s.workout_exercise_id = we.id
  and we.session_id = ws.id
  and ws.user_id::text like '11111111-1111-4111-8111-%';

delete from public.workout_exercises we
using public.workout_sessions ws
where we.session_id = ws.id
  and ws.user_id::text like '11111111-1111-4111-8111-%';

delete from public.workout_sessions
where user_id::text like '11111111-1111-4111-8111-%';

delete from public.ai_chat_usage
where user_id::text like '11111111-1111-4111-8111-%';

delete from public.proactive_coach_messages
where user_id::text like '11111111-1111-4111-8111-%';

delete from public.email_automation_events
where user_id::text like '11111111-1111-4111-8111-%';

delete from public.onboarding_strength_snapshots
where user_id::text like '11111111-1111-4111-8111-%';

delete from public.ops_notes
where user_id::text like '11111111-1111-4111-8111-%';

delete from public.profiles
where id::text like '11111111-1111-4111-8111-%';

-- 2) Exercises referenced by the seed -------------------------------------
insert into public.exercises (name, muscle_group, type, equipment) values
  ('Bench Press', 'Chest', 'compound', 'barbell'),
  ('Incline Bench Press', 'Chest', 'compound', 'barbell'),
  ('Dumbbell Bench Press', 'Chest', 'compound', 'dumbbell'),
  ('Chest Fly', 'Chest', 'isolation', 'dumbbell'),
  ('Cable Fly', 'Chest', 'isolation', 'cable'),
  ('Deadlift', 'Back', 'compound', 'barbell'),
  ('Bent Over Row', 'Back', 'compound', 'barbell'),
  ('Pull-ups', 'Back', 'compound', 'bodyweight'),
  ('Lat Pulldown', 'Back', 'compound', 'cable'),
  ('Seated Cable Row', 'Back', 'compound', 'cable'),
  ('Squat', 'Legs', 'compound', 'barbell'),
  ('Front Squat', 'Legs', 'compound', 'barbell'),
  ('Romanian Deadlift', 'Legs', 'compound', 'barbell'),
  ('Leg Press', 'Legs', 'compound', 'machine'),
  ('Leg Extension', 'Legs', 'isolation', 'machine'),
  ('Leg Curl', 'Legs', 'isolation', 'machine'),
  ('Calf Raise', 'Legs', 'isolation', 'machine'),
  ('Overhead Press', 'Shoulders', 'compound', 'barbell'),
  ('Dumbbell Shoulder Press', 'Shoulders', 'compound', 'dumbbell'),
  ('Lateral Raise', 'Shoulders', 'isolation', 'dumbbell'),
  ('Barbell Curl', 'Biceps', 'isolation', 'barbell'),
  ('Dumbbell Curl', 'Biceps', 'isolation', 'dumbbell'),
  ('Hammer Curl', 'Biceps', 'isolation', 'dumbbell'),
  ('Tricep Pushdown', 'Triceps', 'isolation', 'cable'),
  ('Skull Crusher', 'Triceps', 'isolation', 'barbell'),
  ('Running', 'Cardio', 'cardio', 'bodyweight'),
  ('Cycling', 'Cardio', 'cardio', 'equipment'),
  ('Rowing', 'Cardio', 'cardio', 'machine'),
  ('Incline Walk', 'Cardio', 'cardio', 'machine')
on conflict (name) do nothing;

-- 3) Session-scoped helper functions --------------------------------------
create or replace function pg_temp.uid(n integer) returns uuid as $$
  select ('11111111-1111-4111-8111-' || lpad(n::text, 12, '0'))::uuid;
$$ language sql immutable;

create or replace function pg_temp.mk_user(
  n integer, tag text, name text, goals text[], commitment text[],
  freq text, exp text, coach text, trial_days numeric,
  gender text, age integer
) returns uuid as $$
declare uid uuid := pg_temp.uid(n);
begin
  insert into public.profiles (
    id, user_tag, display_name, goals, commitment, commitment_frequency,
    experience_level, coach, gender, age, trial_start_date, created_at
  ) values (
    uid, tag, name, goals, commitment, freq, exp, coach, gender, age,
    case when trial_days is null then null else now() - (trial_days || ' days')::interval end,
    now() - ((30 + n) || ' days')::interval
  );
  return uid;
end;
$$ language plpgsql;

create or replace function pg_temp.add_workout(
  uid uuid, days_ago numeric, raw text, processing boolean,
  ex_names text[], reps integer, weight numeric, rpe numeric, n_sets integer
) returns void as $$
declare
  sid uuid;
  ex_name text;
  ex_id uuid;
  ord integer := 0;
  s integer;
  ts timestamptz := now() - (days_ago || ' days')::interval;
begin
  insert into public.workout_sessions (user_id, date, raw_text, is_processing, created_at)
  values (uid, ts, raw, processing, ts)
  returning id into sid;

  foreach ex_name in array ex_names loop
    select id into ex_id from public.exercises where name = ex_name;
    if ex_id is null then continue; end if;
    ord := ord + 1;
    insert into public.workout_exercises (session_id, exercise_id, order_index)
    values (sid, ex_id, ord)
    returning id into ex_id;  -- reuse var to hold workout_exercise id
    for s in 1..n_sets loop
      insert into public.sets (workout_exercise_id, set_number, reps, weight, rpe)
      values (
        ex_id, s, reps,
        case when weight = 0 then null else weight end,
        rpe
      );
    end loop;
  end loop;
end;
$$ language plpgsql;

create or replace function pg_temp.add_chat(uid uuid, n integer) returns void as $$
declare i integer;
begin
  for i in 1..n loop
    insert into public.ai_chat_usage (user_id, created_at)
    values (uid, now() - ((i * 0.7) || ' days')::interval);
  end loop;
end;
$$ language plpgsql;

create or replace function pg_temp.add_coach(
  uid uuid, trigger text, days_ago numeric, consumed boolean, coach text
) returns void as $$
begin
  insert into public.proactive_coach_messages (
    user_id, trigger_type, coach_id, body, created_at, consumed_at
  ) values (
    uid, trigger, coach,
    'Hey, ready to train today? Let''s keep the momentum going.',
    now() - (days_ago || ' days')::interval,
    case when consumed then now() - ((days_ago - 0.2) || ' days')::interval else null end
  );
end;
$$ language plpgsql;

create or replace function pg_temp.add_email(
  uid uuid, source text, email_type text, days_ago numeric
) returns void as $$
begin
  insert into public.email_automation_events (
    source, source_event_id, email_type, user_id, recipient_email, status, created_at
  ) values (
    source, gen_random_uuid()::text, email_type, uid,
    'user@demo.repai', 'sent', now() - (days_ago || ' days')::interval
  );
end;
$$ language plpgsql;

create or replace function pg_temp.add_strength(
  uid uuid, ex_name text, weight numeric, reps integer
) returns void as $$
declare ex_id uuid;
begin
  select id into ex_id from public.exercises where name = ex_name;
  insert into public.onboarding_strength_snapshots (
    user_id, exercise_id, working_weight_kg, reps, estimated_1rm_kg
  ) values (uid, ex_id, weight, reps, round(weight * (1 + reps / 30.0), 1))
  on conflict (user_id) do nothing;
end;
$$ language plpgsql;

-- 4) Seed users + activity ------------------------------------------------
do $$
declare u uuid;
begin
  -- ===== Powerlifting-leaning (heavy big-3, low reps, hits commitment) ====
  u := pg_temp.mk_user(1, 'sam_strength', 'Sam', array['gain_strength'], null, '4_times', 'advanced', 'atlas', null, 'male', 29);
  perform pg_temp.add_strength(u, 'Squat', 140, 3);
  perform pg_temp.add_workout(u, 1, 'Squat 160kg 5x3, then pause squats 3x2', false, array['Squat','Front Squat'], 3, 160, 8, 5);
  perform pg_temp.add_workout(u, 3, 'Bench 120 triples, close grip after', false, array['Bench Press','Skull Crusher'], 3, 120, 8, 5);
  perform pg_temp.add_workout(u, 5, 'Deadlift day. 200kg singles then back off', false, array['Deadlift','Bent Over Row'], 3, 200, 9, 4);
  perform pg_temp.add_workout(u, 8, 'OHP 5x5 80kg, pullups', false, array['Overhead Press','Pull-ups'], 5, 80, 7, 5);
  perform pg_temp.add_chat(u, 4);

  u := pg_temp.mk_user(2, 'deadlift_dan', 'Dan', array['gain_strength'], array['monday','wednesday','friday'], null, 'advanced', 'atlas', null, 'male', 34);
  perform pg_temp.add_workout(u, 2, 'Conventional pulls up to 210, beltless backoff', false, array['Deadlift','Romanian Deadlift'], 2, 210, 9, 4);
  perform pg_temp.add_workout(u, 4, 'Comp squat 180 5x3', false, array['Squat'], 3, 180, 8, 5);
  perform pg_temp.add_workout(u, 6, 'Bench triples 130', false, array['Bench Press','Incline Bench Press'], 3, 130, 8, 4);
  perform pg_temp.add_chat(u, 2);

  u := pg_temp.mk_user(3, 'squat_sara', 'Sara', array['gain_strength','build_muscle'], null, '3_times', 'intermediate', 'nova', null, 'female', 27);
  perform pg_temp.add_workout(u, 1, 'High bar squats 5x4 at 90kg', false, array['Squat','Leg Press'], 4, 90, 8, 5);
  perform pg_temp.add_workout(u, 4, 'Deadlift 120 for triples', false, array['Deadlift'], 3, 120, 8, 4);
  perform pg_temp.add_workout(u, 7, 'Bench 4x5 60kg', false, array['Bench Press','Overhead Press'], 5, 60, 7, 4);

  u := pg_temp.mk_user(4, 'press_pete', 'Pete', array['gain_strength'], null, '4_times', 'advanced', 'atlas', null, 'male', 41);
  perform pg_temp.add_workout(u, 2, 'Push press heavy singles 100kg', false, array['Overhead Press','Bench Press'], 2, 100, 9, 4);
  perform pg_temp.add_workout(u, 5, 'Front squat triples', false, array['Front Squat','Squat'], 3, 130, 8, 4);

  -- ===== Bodybuilding-leaning (split, isolation, 8-12 reps) ===============
  u := pg_temp.mk_user(5, 'hypertrophy_hana', 'Hana', array['build_muscle'], null, '5_plus', 'intermediate', 'nova', null, 'female', 25);
  perform pg_temp.add_workout(u, 1, 'Push day: incline db press, cable fly, lateral raises, pushdowns', false, array['Dumbbell Bench Press','Cable Fly','Lateral Raise','Tricep Pushdown'], 10, 24, 8, 4);
  perform pg_temp.add_workout(u, 2, 'Pull day: lat pulldown, cable row, curls', false, array['Lat Pulldown','Seated Cable Row','Dumbbell Curl','Hammer Curl'], 11, 30, 8, 4);
  perform pg_temp.add_workout(u, 3, 'Leg day: leg press, extensions, curls, calves', false, array['Leg Press','Leg Extension','Leg Curl','Calf Raise'], 12, 80, 8, 4);
  perform pg_temp.add_chat(u, 6);

  u := pg_temp.mk_user(6, 'pump_paul', 'Paul', array['build_muscle'], null, '4_times', 'beginner', 'nova', null, 'male', 22);
  perform pg_temp.add_workout(u, 1, 'Chest and tris, lots of volume', false, array['Bench Press','Chest Fly','Cable Fly','Tricep Pushdown'], 12, 40, 7, 4);
  perform pg_temp.add_workout(u, 3, 'Back and bis', false, array['Lat Pulldown','Seated Cable Row','Dumbbell Curl'], 10, 35, 8, 4);
  perform pg_temp.add_workout(u, 5, 'Shoulders', false, array['Dumbbell Shoulder Press','Lateral Raise'], 12, 18, 7, 4);

  u := pg_temp.mk_user(7, 'split_steve', 'Steve', array['build_muscle'], array['monday','tuesday','thursday','friday'], null, 'intermediate', 'max', null, 'male', 31);
  perform pg_temp.add_workout(u, 2, 'Arm day, curls and extensions supersets', false, array['Barbell Curl','Hammer Curl','Skull Crusher','Tricep Pushdown'], 10, 25, 8, 4);
  perform pg_temp.add_workout(u, 4, 'Chest hypertrophy', false, array['Incline Bench Press','Chest Fly'], 10, 50, 8, 4);

  u := pg_temp.mk_user(8, 'aesthetic_amy', 'Amy', array['build_muscle','lose_fat'], null, '4_times', 'intermediate', 'nova', null, 'female', 28);
  perform pg_temp.add_workout(u, 1, 'Glutes and quads, high reps', false, array['Leg Press','Leg Extension','Leg Curl'], 12, 70, 8, 4);
  perform pg_temp.add_workout(u, 3, 'Shoulders and back', false, array['Lateral Raise','Lat Pulldown','Seated Cable Row'], 12, 22, 7, 4);
  perform pg_temp.add_chat(u, 3);

  -- ===== Cardio / general fitness =========================================
  u := pg_temp.mk_user(9, 'cardio_kate', 'Kate', array['lose_fat','general_fitness'], null, '4_times', 'beginner', 'nova', null, 'female', 33);
  perform pg_temp.add_workout(u, 1, '5k run, easy pace', false, array['Running'], 1, 0, null, 1);
  perform pg_temp.add_workout(u, 2, '30 min cycling intervals', false, array['Cycling'], 1, 0, null, 1);
  perform pg_temp.add_workout(u, 4, 'Rowing 5000m', false, array['Rowing'], 1, 0, null, 1);
  perform pg_temp.add_chat(u, 2);

  u := pg_temp.mk_user(10, 'runner_raj', 'Raj', array['general_fitness'], null, '5_plus', 'intermediate', 'max', null, 'male', 38);
  perform pg_temp.add_workout(u, 1, '10k tempo run', false, array['Running'], 1, 0, null, 1);
  perform pg_temp.add_workout(u, 2, 'Incline treadmill walk 45 min', false, array['Incline Walk'], 1, 0, null, 1);
  perform pg_temp.add_workout(u, 3, 'Easy 5k recovery', false, array['Running'], 1, 0, null, 1);

  u := pg_temp.mk_user(11, 'row_rosa', 'Rosa', array['lose_fat','general_fitness'], null, '3_times', 'beginner', 'nova', null, 'female', 45);
  perform pg_temp.add_workout(u, 2, 'Rowing then some light squats', false, array['Rowing','Squat'], 12, 40, 6, 2);
  perform pg_temp.add_workout(u, 5, 'Bike + core', false, array['Cycling'], 1, 0, null, 1);

  -- ===== Commitment gap (high stated commitment, few/no workouts) =========
  u := pg_temp.mk_user(12, 'busy_ben', 'Ben', array['build_muscle'], null, '4_times', 'beginner', 'max', null, 'male', 36);
  perform pg_temp.add_workout(u, 9, 'Quick full body, been slammed at work', false, array['Squat','Bench Press','Lat Pulldown'], 8, 50, 7, 3);
  perform pg_temp.add_chat(u, 1);

  u := pg_temp.mk_user(13, 'ghost_gina', 'Gina', array['lose_fat'], null, '5_plus', 'beginner', 'nova', null, 'female', 30);
  -- No workouts at all despite 5x/week commitment.

  u := pg_temp.mk_user(14, 'flaky_fred', 'Fred', array['build_muscle'], array['monday','tuesday','thursday','friday'], null, 'beginner', 'max', null, 'male', 24);
  perform pg_temp.add_workout(u, 11, 'First session, felt good', false, array['Bench Press','Lat Pulldown'], 10, 40, 7, 3);

  u := pg_temp.mk_user(15, 'slipping_sue', 'Sue', array['general_fitness'], array['monday','wednesday','friday','saturday'], null, 'intermediate', 'nova', null, 'female', 42);
  perform pg_temp.add_workout(u, 10, 'Full body, getting back into it', false, array['Leg Press','Seated Cable Row'], 10, 60, 7, 3);

  -- ===== Trial going quiet (trial started recently, no recent activity) ===
  u := pg_temp.mk_user(16, 'trial_tom', 'Tom', array['build_muscle'], null, '3_times', 'beginner', 'nova', 3, 'male', 26);
  perform pg_temp.add_email(u, 'revenuecat', 'trial_started', 3);
  -- Started trial 3 days ago, never logged a workout.

  u := pg_temp.mk_user(17, 'trial_tina', 'Tina', array['lose_fat'], null, '4_times', 'beginner', 'nova', 6, 'female', 29);
  perform pg_temp.add_email(u, 'revenuecat', 'trial_started', 6);
  perform pg_temp.add_workout(u, 6, 'Tried the app, logged my first workout', false, array['Leg Press','Lat Pulldown'], 10, 50, 7, 3);
  -- One workout 6 days ago, quiet since.

  u := pg_temp.mk_user(18, 'trial_theo', 'Theo', array['gain_strength'], null, '4_times', 'intermediate', 'atlas', 8, 'male', 35);
  perform pg_temp.add_email(u, 'revenuecat', 'trial_started', 8);
  -- Trial 8 days ago, never active.

  -- ===== Active power users (high frequency, coach consumed) ==============
  u := pg_temp.mk_user(19, 'power_pat', 'Pat', array['build_muscle','gain_strength'], null, '5_plus', 'advanced', 'atlas', null, 'male', 30);
  perform pg_temp.add_workout(u, 0.5, 'Upper power', false, array['Bench Press','Overhead Press','Pull-ups'], 5, 90, 8, 5);
  perform pg_temp.add_workout(u, 1.5, 'Lower power', false, array['Squat','Romanian Deadlift'], 5, 140, 8, 5);
  perform pg_temp.add_workout(u, 2.5, 'Upper hypertrophy', false, array['Incline Bench Press','Lateral Raise','Barbell Curl'], 10, 50, 8, 4);
  perform pg_temp.add_workout(u, 3.5, 'Lower hypertrophy', false, array['Leg Press','Leg Curl','Calf Raise'], 12, 100, 8, 4);
  perform pg_temp.add_workout(u, 5, 'Accessory pump', false, array['Cable Fly','Tricep Pushdown','Hammer Curl'], 12, 25, 8, 3);
  perform pg_temp.add_chat(u, 9);
  perform pg_temp.add_coach(u, 'workout_day_morning', 1, true, 'atlas');
  perform pg_temp.add_coach(u, 'post_workout_followup', 2, true, 'atlas');

  u := pg_temp.mk_user(20, 'daily_dana', 'Dana', array['build_muscle'], null, '5_plus', 'intermediate', 'nova', null, 'female', 27);
  perform pg_temp.add_workout(u, 0.5, 'Push', false, array['Dumbbell Bench Press','Lateral Raise'], 10, 22, 8, 4);
  perform pg_temp.add_workout(u, 1.5, 'Pull', false, array['Lat Pulldown','Dumbbell Curl'], 10, 30, 8, 4);
  perform pg_temp.add_workout(u, 2.5, 'Legs', false, array['Leg Press','Leg Extension'], 12, 80, 8, 4);
  perform pg_temp.add_chat(u, 7);
  perform pg_temp.add_coach(u, 'workout_day_morning', 1, true, 'nova');

  u := pg_temp.mk_user(21, 'grind_greg', 'Greg', array['gain_strength','build_muscle'], null, '4_times', 'advanced', 'atlas', null, 'male', 33);
  perform pg_temp.add_workout(u, 1, 'Heavy squats and accessories', false, array['Squat','Leg Press','Leg Curl'], 5, 150, 8, 5);
  perform pg_temp.add_workout(u, 3, 'Bench and back', false, array['Bench Press','Bent Over Row'], 5, 110, 8, 5);
  perform pg_temp.add_workout(u, 5, 'Deadlift and pulls', false, array['Deadlift','Pull-ups'], 4, 180, 8, 4);
  perform pg_temp.add_coach(u, 'comeback', 2, true, 'atlas');

  -- ===== Coach ignored (messages sent, never consumed) ====================
  u := pg_temp.mk_user(22, 'ignored_ivan', 'Ivan', array['build_muscle'], null, '3_times', 'beginner', 'max', null, 'male', 28);
  perform pg_temp.add_workout(u, 7, 'One workout then went quiet', false, array['Bench Press','Lat Pulldown'], 10, 45, 7, 3);
  perform pg_temp.add_coach(u, 'missed_workout', 5, false, 'max');
  perform pg_temp.add_coach(u, 'missed_workout', 3, false, 'max');
  perform pg_temp.add_coach(u, 'comeback', 1, false, 'max');

  u := pg_temp.mk_user(23, 'silent_sam', 'Sammy', array['lose_fat'], null, '4_times', 'beginner', 'nova', null, 'female', 39);
  perform pg_temp.add_coach(u, 'missed_workout', 4, false, 'nova');
  perform pg_temp.add_coach(u, 'comeback', 2, false, 'nova');

  -- ===== Stuck parse (is_processing stuck beyond threshold) ===============
  u := pg_temp.mk_user(24, 'stuck_stan', 'Stan', array['build_muscle'], null, '3_times', 'intermediate', 'max', null, 'male', 32);
  perform pg_temp.add_workout(u, 4, 'Solid push session', false, array['Bench Press','Overhead Press'], 8, 70, 7, 4);
  perform pg_temp.add_workout(u, 0.02, 'did chest n tris — bench 3x8 incline db press supersetted with rope pushdowns idk the weights', true, array['Bench Press'], 8, 70, 7, 1);

  u := pg_temp.mk_user(25, 'parse_pam', 'Pam', array['general_fitness'], null, '3_times', 'beginner', 'nova', null, 'female', 37);
  perform pg_temp.add_workout(u, 0.03, 'leg day quads n hammies, leg press felt heavy today maybe 4 plates each side', true, array['Leg Press'], 12, 100, 7, 1);
end $$;
