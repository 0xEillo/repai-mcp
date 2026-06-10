from datetime import datetime, timedelta, timezone

import pytest

from repai_mcp.queries.users import UserNotFoundError
from repai_mcp.store import InMemoryRepAIStore
from repai_mcp.tools.investigate import build_user_digest, investigate_user

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)


def iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def we(name, muscle, type_, equipment, reps):
    return {
        "exercises": {"name": name, "muscle_group": muscle, "type": type_,
                      "equipment": equipment},
        "sets": [{"reps": r} for r in reps],
    }


def sample_profile():
    return {
        "id": "u1",
        "user_tag": "sam_strength",
        "display_name": "Sam",
        "gender": "male",
        "age": 29,
        "experience_level": "advanced",
        "coach": "atlas",
        "is_guest": False,
        "overall_strength_score": 88,
        "overall_strength_level": "advanced",
        "goals": ["gain_strength"],
        "commitment": None,
        "commitment_frequency": "4_times",
    }


def test_build_user_digest_full():
    sessions = [
        {"id": "s1", "date": iso(1), "raw_text": "Squat 5x3 160kg",
         "workout_exercises": [we("Squat", "Legs", "compound", "barbell",
                                  [3, 3, 3])]},
        {"id": "s2", "date": iso(5), "raw_text": "Deadlift singles",
         "workout_exercises": [we("Deadlift", "Back", "compound", "barbell",
                                  [1, 1])]},
    ]
    coach = [
        {"trigger_type": "workout_day_morning", "consumed_at": iso(0.5)},
        {"trigger_type": "comeback", "consumed_at": None},
    ]
    emails = [
        {"email_type": "trial_started"},
        {"email_type": "trial_started"},
        {"email_type": "weekly_recap"},
    ]
    strength = {"working_weight_kg": 140.0, "reps": 3, "estimated_1rm_kg": 154.0,
                "exercises": {"name": "Squat"}}

    digest = build_user_digest(
        sample_profile(), sessions, 4, coach, emails, strength, now=NOW
    )

    assert digest.profile.user_tag == "sam_strength"
    assert digest.profile.overall_strength_score == 88
    assert digest.intent.weekly_target == 4  # 4_times frequency
    assert digest.workouts.total_sessions == 2
    assert digest.workouts.days_since_last_workout == 1
    assert digest.workouts.recent[0].exercise_count == 1
    assert digest.workouts.recent[0].raw_text_preview == "Squat 5x3 160kg"
    assert digest.ai_chat_usage_count == 4
    assert digest.coach_engagement.sent == 2
    assert digest.coach_engagement.consumed == 1
    assert digest.coach_engagement.consumption_rate == 0.5
    assert digest.email_activity.total == 3
    by_type = {e.email_type: e.count for e in digest.email_activity.by_type}
    assert by_type == {"trial_started": 2, "weekly_recap": 1}
    assert digest.strength_snapshot.exercise == "Squat"
    assert digest.signals.compound_ratio == 1.0  # both compound
    assert digest.signals.total_exercises == 2


def test_build_user_digest_no_activity():
    digest = build_user_digest(
        sample_profile(), [], 0, [], [], None, now=NOW
    )
    assert digest.workouts.total_sessions == 0
    assert digest.workouts.days_since_last_workout is None
    assert digest.workouts.last_session_date is None
    assert digest.coach_engagement.consumption_rate == 0.0
    assert digest.email_activity.total == 0
    assert digest.strength_snapshot is None
    assert digest.signals.avg_reps is None


def test_investigate_user_unknown_tag_raises():
    with pytest.raises(UserNotFoundError, match="ghost"):
        investigate_user(InMemoryRepAIStore(), user_tag="ghost")


def test_investigate_user_uses_store_public_interface():
    store = InMemoryRepAIStore(
        profiles=[sample_profile()],
        workout_sessions=[
            {
                "id": "s1",
                "user_id": "u1",
                "date": iso(1),
                "raw_text": "Squat 5x3 160kg",
                "workout_exercises": [
                    we("Squat", "Legs", "compound", "barbell", [3, 3, 3])
                ],
            }
        ],
        ai_chat_usage=[{"user_id": "u1"}, {"user_id": "u1"}],
        proactive_coach_messages=[
            {"user_id": "u1", "trigger_type": "comeback", "consumed_at": iso(0.5)}
        ],
        email_automation_events=[
            {"user_id": "u1", "email_type": "trial_started"}
        ],
        onboarding_strength_snapshots=[
            {
                "user_id": "u1",
                "working_weight_kg": 140.0,
                "reps": 3,
                "estimated_1rm_kg": 154.0,
                "exercises": {"name": "Squat"},
            }
        ],
    )

    digest = investigate_user(store, user_tag="sam_strength")

    assert digest.profile.user_tag == "sam_strength"
    assert digest.workouts.total_sessions == 1
    assert digest.ai_chat_usage_count == 2
    assert digest.coach_engagement.consumption_rate == 1.0
    assert digest.email_activity.total == 1
    assert digest.strength_snapshot is not None
