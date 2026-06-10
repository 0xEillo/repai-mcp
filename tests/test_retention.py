from datetime import datetime, timezone

from repai_mcp.store import InMemoryRepAIStore
from repai_mcp.tools.retention import (
    compute_coach_engagement,
    compute_commitment_gaps,
    compute_stuck_sessions,
    compute_trial_dropoff,
    find_commitment_gaps,
    find_stuck_workout_sessions,
    find_trial_dropoff_risk,
    summarize_coach_engagement,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def iso(days_ago: float) -> str:
    from datetime import timedelta

    return (NOW - timedelta(days=days_ago)).isoformat()


# --------------------------------------------------------------------------- #
# commitment gaps
# --------------------------------------------------------------------------- #
def test_commitment_gaps_flags_underperformers_only():
    profiles = [
        {"id": "a", "user_tag": "keen", "display_name": "Keen",
         "commitment": ["monday", "wednesday", "friday", "saturday"],
         "commitment_frequency": None},  # target 4
        {"id": "b", "user_tag": "ontrack", "display_name": None,
         "commitment": None, "commitment_frequency": "2_times"},  # target 2
        {"id": "c", "user_tag": "nocommit", "display_name": None,
         "commitment": None, "commitment_frequency": None},  # skipped
    ]
    # 14-day window = 2 weeks. a: 2 workouts -> 1/wk (gap 3). b: 4 -> 2/wk (gap 0).
    sessions = (
        [{"user_id": "a", "date": iso(1)}, {"user_id": "a", "date": iso(3)}]
        + [{"user_id": "b", "date": iso(i)} for i in range(1, 5)]
    )

    result = compute_commitment_gaps(
        profiles, sessions, lookback_days=14, min_gap_per_week=1.0, limit=50
    )

    assert result.count == 1
    gap = result.users[0]
    assert gap.user_tag == "keen"
    assert gap.weekly_target == 4
    assert gap.workouts_in_window == 2
    assert gap.actual_per_week == 1.0
    assert gap.gap_per_week == 3.0


def test_commitment_gaps_sorted_by_gap_desc_and_limited():
    profiles = [
        {"id": "a", "user_tag": "a", "display_name": None,
         "commitment": None, "commitment_frequency": "5_plus"},
        {"id": "b", "user_tag": "b", "display_name": None,
         "commitment": None, "commitment_frequency": "2_times"},
    ]
    result = compute_commitment_gaps(
        profiles, [], lookback_days=7, min_gap_per_week=1.0, limit=1
    )
    assert result.count == 2  # total found
    assert len(result.users) == 1  # limited
    assert result.users[0].user_tag == "a"  # bigger gap (5 vs 2)


# --------------------------------------------------------------------------- #
# trial dropoff
# --------------------------------------------------------------------------- #
def test_trial_dropoff_flags_quiet_and_never_active():
    profiles = [
        {"id": "never", "user_tag": "never", "display_name": None,
         "trial_start_date": iso(3)},
        {"id": "quiet", "user_tag": "quiet", "display_name": None,
         "trial_start_date": iso(6)},
        {"id": "active", "user_tag": "active", "display_name": None,
         "trial_start_date": iso(4)},
    ]
    sessions = [
        {"user_id": "quiet", "date": iso(6)},   # last workout 6 days ago -> quiet
        {"user_id": "active", "date": iso(1)},  # worked out yesterday -> ok
    ]

    result = compute_trial_dropoff(
        profiles, sessions, now=NOW, trial_window_days=14,
        inactive_days=5, limit=50,
    )

    tags = [u.user_tag for u in result.users]
    assert "active" not in tags
    assert result.count == 2
    # never-active sorted first
    assert result.users[0].user_tag == "never"
    assert result.users[0].days_since_last_workout is None
    assert result.users[0].workouts_since_trial_start == 0


def test_trial_dropoff_ignores_workouts_before_trial_start():
    profiles = [
        {"id": "u", "user_tag": "u", "display_name": None,
         "trial_start_date": iso(3)},
    ]
    sessions = [{"user_id": "u", "date": iso(10)}]  # before trial start

    result = compute_trial_dropoff(
        profiles, sessions, now=NOW, trial_window_days=14,
        inactive_days=5, limit=50,
    )
    assert result.count == 1
    assert result.users[0].workouts_since_trial_start == 0


# --------------------------------------------------------------------------- #
# stuck sessions
# --------------------------------------------------------------------------- #
def test_stuck_sessions_filters_by_threshold_and_previews_text():
    sessions = [
        {"id": "s1", "user_id": "u1",
         "created_at": (NOW.replace(microsecond=0)).isoformat(),
         "raw_text": "fresh"},  # 0 min -> excluded
        {"id": "s2", "user_id": "u1",
         "created_at": iso(0.5),  # 12 hours -> stuck
         "raw_text": "x" * 200},
    ]
    result = compute_stuck_sessions(
        sessions, {"u1": "lifter"}, now=NOW, older_than_minutes=15, limit=50
    )
    assert result.count == 1
    s = result.sessions[0]
    assert s.session_id == "s2"
    assert s.user_tag == "lifter"
    assert s.raw_text_preview.endswith("…")
    assert len(s.raw_text_preview) <= 141


def test_stuck_sessions_handles_missing_user_tag():
    sessions = [{"id": "s1", "user_id": "ghost", "created_at": iso(1),
                 "raw_text": None}]
    result = compute_stuck_sessions(
        sessions, {}, now=NOW, older_than_minutes=15, limit=50
    )
    assert result.sessions[0].user_tag is None
    assert result.sessions[0].raw_text_preview is None


# --------------------------------------------------------------------------- #
# coach engagement
# --------------------------------------------------------------------------- #
def test_coach_engagement_aggregates_and_groups():
    messages = [
        {"trigger_type": "missed_workout", "created_at": iso(1),
         "consumed_at": iso(0.5)},
        {"trigger_type": "missed_workout", "created_at": iso(2),
         "consumed_at": None},
        {"trigger_type": "comeback", "created_at": iso(3),
         "consumed_at": iso(2)},
    ]
    result = compute_coach_engagement(messages, lookback_days=30)

    assert result.total_sent == 3
    assert result.total_consumed == 2
    assert result.consumption_rate == round(2 / 3, 3)

    by = {b.trigger_type: b for b in result.by_trigger}
    assert by["missed_workout"].sent == 2
    assert by["missed_workout"].consumed == 1
    assert by["missed_workout"].consumption_rate == 0.5
    assert by["comeback"].consumption_rate == 1.0


def test_coach_engagement_handles_no_messages():
    result = compute_coach_engagement([], lookback_days=30)
    assert result.total_sent == 0
    assert result.consumption_rate == 0.0
    assert result.by_trigger == []


def test_retention_tools_use_store_public_interface():
    store = InMemoryRepAIStore(
        profiles=[
            {
                "id": "u1",
                "user_tag": "quiet",
                "display_name": "Quiet",
                "commitment": None,
                "commitment_frequency": "4_times",
                "trial_start_date": iso(3),
            },
            {
                "id": "u2",
                "user_tag": "active",
                "display_name": "Active",
                "commitment": None,
                "commitment_frequency": "2_times",
                "trial_start_date": iso(3),
            },
        ],
        workout_sessions=[
            {"id": "s1", "user_id": "u2", "date": iso(1), "is_processing": False},
            {
                "id": "stuck",
                "user_id": "u1",
                "created_at": iso(1),
                "raw_text": "Bench 3x8",
                "is_processing": True,
            },
        ],
        proactive_coach_messages=[
            {
                "user_id": "u1",
                "trigger_type": "comeback",
                "created_at": iso(1),
                "consumed_at": None,
            }
        ],
    )

    gaps = find_commitment_gaps(store, lookback_days=14, limit=10)
    dropoff = find_trial_dropoff_risk(store, trial_window_days=14, limit=10)
    stuck = find_stuck_workout_sessions(store, older_than_minutes=15, limit=10)
    engagement = summarize_coach_engagement(store, lookback_days=30)

    assert gaps.count == 2
    assert dropoff.count == 1
    assert dropoff.users[0].user_tag == "quiet"
    assert stuck.sessions[0].user_tag == "quiet"
    assert engagement.total_sent == 1
