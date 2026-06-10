from repai_mcp.store import InMemoryRepAIStore
from repai_mcp.tools.cohort import (
    build_workout_samples,
    compute_user_base_summary,
    describe_user_base,
    sample_workout_inputs,
)


# --------------------------------------------------------------------------- #
# sample_workout_inputs
# --------------------------------------------------------------------------- #
def test_build_workout_samples_filters_blank_and_maps_tags():
    sessions = [
        {"id": "s1", "user_id": "u1", "date": "2026-06-01T10:00:00+00:00",
         "raw_text": "  Squat 5x5  "},
        {"id": "s2", "user_id": "u2", "date": "2026-06-02T10:00:00+00:00",
         "raw_text": "   "},  # blank -> skipped
        {"id": "s3", "user_id": "ghost", "date": "2026-06-03T10:00:00+00:00",
         "raw_text": "Run 5k"},
    ]
    result = build_workout_samples(
        sessions, {"u1": "sam", "u2": "dan"}, limit=20
    )
    assert result.count == 2
    first = result.samples[0]
    assert first.session_id == "s1"
    assert first.user_tag == "sam"
    assert first.raw_text == "Squat 5x5"  # stripped
    assert result.samples[1].user_tag is None  # unknown user_id


def test_build_workout_samples_respects_limit():
    sessions = [
        {"id": f"s{i}", "user_id": "u", "date": "2026-06-01T00:00:00+00:00",
         "raw_text": f"workout {i}"}
        for i in range(5)
    ]
    result = build_workout_samples(sessions, {"u": "tag"}, limit=2)
    assert result.count == 2
    assert len(result.samples) == 2


# --------------------------------------------------------------------------- #
# describe_user_base
# --------------------------------------------------------------------------- #
def we(name, muscle, type_, equipment, reps):
    return {
        "exercises": {"name": name, "muscle_group": muscle, "type": type_,
                      "equipment": equipment},
        "sets": [{"reps": r} for r in reps],
    }


def test_compute_user_base_summary_aggregates_active_only():
    profiles = [
        {"id": "u1", "goals": ["build_muscle"], "experience_level": "advanced",
         "is_guest": False},
        {"id": "u2", "goals": ["build_muscle", "lose_fat"],
         "experience_level": "beginner", "is_guest": False},
        {"id": "u3", "goals": ["general_fitness"],
         "experience_level": "beginner", "is_guest": False},  # inactive
        {"id": "g1", "goals": ["lose_fat"], "experience_level": "beginner",
         "is_guest": True},  # guest -> excluded entirely
    ]
    sessions = [
        {"id": "s1", "user_id": "u1",
         "workout_exercises": [
             we("Squat", "Legs", "compound", "barbell", [5, 5]),
         ]},
        {"id": "s2", "user_id": "u2",
         "workout_exercises": [
             we("Leg Curl", "Legs", "isolation", "machine", [12]),
         ]},
    ]

    summary = compute_user_base_summary(profiles, sessions, lookback_days=90)

    assert summary.total_users == 3  # non-guest
    assert summary.active_users == 2  # u1, u2 (u3 has no session)
    assert summary.signals.total_exercises == 2
    assert summary.signals.compound_ratio == 0.5

    goals = {c.label: c.count for c in summary.goal_distribution}
    assert goals["build_muscle"] == 2  # u1 + u2
    assert goals["lose_fat"] == 1
    assert "general_fitness" not in goals  # u3 inactive

    exp = {c.label: c.count for c in summary.experience_level_breakdown}
    assert exp == {"advanced": 1, "beginner": 1}


def test_compute_user_base_summary_handles_no_activity():
    profiles = [
        {"id": "u1", "goals": ["build_muscle"], "experience_level": "beginner",
         "is_guest": False},
    ]
    summary = compute_user_base_summary(profiles, [], lookback_days=30)
    assert summary.total_users == 1
    assert summary.active_users == 0
    assert summary.signals.total_exercises == 0
    assert summary.goal_distribution == []
    assert summary.experience_level_breakdown == []


def test_cohort_tools_use_store_public_interface():
    store = InMemoryRepAIStore(
        profiles=[
            {
                "id": "u1",
                "user_tag": "sam",
                "display_name": "Sam",
                "goals": ["build_muscle"],
                "experience_level": "advanced",
                "is_guest": False,
            }
        ],
        workout_sessions=[
            {
                "id": "s1",
                "user_id": "u1",
                "date": "2026-06-09T00:00:00+00:00",
                "raw_text": "Squat 5x5",
                "is_processing": False,
                "workout_exercises": [
                    we("Squat", "Legs", "compound", "barbell", [5, 5])
                ],
            }
        ],
    )

    samples = sample_workout_inputs(store, user_tag="sam", limit=5)
    summary = describe_user_base(store, lookback_days=90)

    assert samples.count == 1
    assert samples.samples[0].user_tag == "sam"
    assert summary.total_users == 1
    assert summary.active_users == 1
