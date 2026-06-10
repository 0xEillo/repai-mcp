from repai_mcp.queries.signals import (
    ExerciseEntry,
    categorical_distribution,
    compute_training_signals,
    flatten_exercise_entries,
)


def session(*workout_exercises):
    return {"workout_exercises": list(workout_exercises)}


def we(name, muscle_group, type_, equipment, reps):
    return {
        "exercises": {
            "name": name,
            "muscle_group": muscle_group,
            "type": type_,
            "equipment": equipment,
        },
        "sets": [{"reps": r} for r in reps],
    }


def test_flatten_skips_unnamed_and_collects_reps():
    sessions = [
        session(
            we("Squat", "Legs", "compound", "barbell", [5, 5, 3]),
            {"exercises": None, "sets": [{"reps": 10}]},  # no exercise -> skip
        )
    ]
    entries = flatten_exercise_entries(sessions)
    assert len(entries) == 1
    assert entries[0].name == "Squat"
    assert entries[0].reps == [5, 5, 3]


def test_flatten_ignores_null_reps():
    sessions = [
        session(we("Running", "Cardio", "cardio", "bodyweight", [])),
    ]
    sessions[0]["workout_exercises"][0]["sets"] = [{"reps": None}, {"reps": 1}]
    entries = flatten_exercise_entries(sessions)
    assert entries[0].reps == [1]


def test_compute_training_signals_aggregates():
    entries = [
        ExerciseEntry(name="Squat", muscle_group="Legs", type="compound",
                      equipment="barbell", reps=[5, 5]),
        ExerciseEntry(name="Squat", muscle_group="Legs", type="compound",
                      equipment="barbell", reps=[3]),
        ExerciseEntry(name="Leg Curl", muscle_group="Legs", type="isolation",
                      equipment="machine", reps=[12]),
        ExerciseEntry(name="Lateral Raise", muscle_group="Shoulders",
                      type="isolation", equipment="dumbbell", reps=[15, 15]),
    ]
    s = compute_training_signals(entries, top_n=2)

    assert s.total_exercises == 4
    assert s.total_sets == 6
    # reps: 5,5,3,12,15,15 -> 55/6
    assert s.avg_reps == round(55 / 6, 1)
    # compound 2, isolation 2 -> 0.5
    assert s.compound_ratio == 0.5

    top = {c.label: c.count for c in s.top_exercises}
    assert top["Squat"] == 2
    assert len(s.top_exercises) == 2  # limited by top_n

    muscle = {c.label: (c.count, c.share) for c in s.muscle_group_distribution}
    assert muscle["Legs"] == (3, round(3 / 4, 3))


def test_compute_training_signals_empty():
    s = compute_training_signals([])
    assert s.total_exercises == 0
    assert s.total_sets == 0
    assert s.avg_reps is None
    assert s.compound_ratio is None
    assert s.muscle_group_distribution == []


def test_compute_training_signals_cardio_only_has_no_ratio():
    entries = [
        ExerciseEntry(name="Running", muscle_group="Cardio", type="cardio",
                      equipment="bodyweight", reps=[1]),
    ]
    s = compute_training_signals(entries)
    assert s.compound_ratio is None


def test_categorical_distribution_counts_and_skips_empty():
    dist = categorical_distribution(["beginner", "beginner", "advanced", None])
    by = {c.label: (c.count, c.share) for c in dist}
    assert by["beginner"] == (2, round(2 / 3, 3))
    assert by["advanced"] == (1, round(1 / 3, 3))
    assert "" not in by
