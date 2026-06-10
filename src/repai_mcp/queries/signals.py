"""Shared training-signal computation.

Pure functions that turn joined workout/exercise/set rows into behavioural
signals — muscle group mix, top exercises, compound/isolation ratio, equipment
breakdown, and average reps. Consumed by the cohort tools in this slice and,
later, by the per-user investigate_user / LLM persona tools (issue 06).

Keeping the maths here (and free of Supabase) gives a single, well-tested seam
that every persona-style tool can reuse.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from pydantic import BaseModel, Field


class ExerciseEntry(BaseModel):
    """One performed exercise within a session, with its per-set reps."""

    name: str
    muscle_group: str | None = None
    type: str | None = None
    equipment: str | None = None
    reps: list[int] = Field(default_factory=list)


class CategoryShare(BaseModel):
    label: str
    count: int
    share: float


class TrainingSignals(BaseModel):
    total_exercises: int
    total_sets: int
    avg_reps: float | None
    compound_ratio: float | None
    muscle_group_distribution: list[CategoryShare]
    type_breakdown: list[CategoryShare]
    equipment_breakdown: list[CategoryShare]
    top_exercises: list[CategoryShare]


def _shares(
    counter: Counter[str], total: int, *, limit: int | None = None
) -> list[CategoryShare]:
    return [
        CategoryShare(
            label=label,
            count=count,
            share=round(count / total, 3) if total else 0.0,
        )
        for label, count in counter.most_common(limit)
    ]


def flatten_exercise_entries(sessions: list[dict]) -> list[ExerciseEntry]:
    """Flatten nested PostgREST workout rows into a flat ExerciseEntry list.

    Expects each session to embed ``workout_exercises`` -> ``exercises`` (to-one)
    and ``sets`` (to-many), as returned by the cohort/user select queries.
    """
    entries: list[ExerciseEntry] = []
    for session in sessions:
        for we in session.get("workout_exercises") or []:
            exercise = we.get("exercises") or {}
            name = exercise.get("name")
            if not name:
                continue
            reps = [
                s["reps"]
                for s in (we.get("sets") or [])
                if s.get("reps") is not None
            ]
            entries.append(
                ExerciseEntry(
                    name=name,
                    muscle_group=exercise.get("muscle_group"),
                    type=exercise.get("type"),
                    equipment=exercise.get("equipment"),
                    reps=reps,
                )
            )
    return entries


def compute_training_signals(
    entries: list[ExerciseEntry], *, top_n: int = 10
) -> TrainingSignals:
    """Aggregate exercise entries into behavioural training signals.

    ``compound_ratio`` is compound / (compound + isolation), ignoring cardio and
    untyped exercises; it is None when no compound/isolation work is present.
    ``avg_reps`` averages over every recorded set and is None when no reps exist.
    """
    muscle: Counter[str] = Counter()
    equipment: Counter[str] = Counter()
    types: Counter[str] = Counter()
    exercises: Counter[str] = Counter()
    reps_sum = 0
    reps_count = 0

    for entry in entries:
        exercises[entry.name] += 1
        if entry.muscle_group:
            muscle[entry.muscle_group] += 1
        if entry.equipment:
            equipment[entry.equipment] += 1
        if entry.type:
            types[entry.type] += 1
        reps_sum += sum(entry.reps)
        reps_count += len(entry.reps)

    total_exercises = len(entries)
    compound = types.get("compound", 0)
    isolation = types.get("isolation", 0)
    typed = compound + isolation

    return TrainingSignals(
        total_exercises=total_exercises,
        total_sets=reps_count,
        avg_reps=round(reps_sum / reps_count, 1) if reps_count else None,
        compound_ratio=round(compound / typed, 3) if typed else None,
        muscle_group_distribution=_shares(muscle, total_exercises),
        type_breakdown=_shares(types, total_exercises),
        equipment_breakdown=_shares(equipment, total_exercises),
        top_exercises=_shares(exercises, total_exercises, limit=top_n),
    )


def categorical_distribution(values: Iterable[str | None]) -> list[CategoryShare]:
    """Count non-empty categorical values into shares over the known total."""
    counter: Counter[str] = Counter(v for v in values if v)
    return _shares(counter, sum(counter.values()))
