"""Qualitative + cohort read tools (SQL only, no LLM).

- sample_workout_inputs: filtered samples of raw user workout text with context
- describe_user_base: cohort-level behavioural aggregates across active users

Both follow the codebase pattern of a thin Supabase fetch plus a pure compute
function, the latter being the unit-test seam. Behavioural aggregation reuses
the shared signal module so the LLM persona slice (issue 06) can build on it.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel

from repai_mcp.llm.persona import (
    LLM_DISABLED_NOTE,
    LLMClient,
    synthesize_user_base,
)
from repai_mcp.queries.signals import (
    CategoryShare,
    TrainingSignals,
    categorical_distribution,
    compute_training_signals,
    flatten_exercise_entries,
)
from repai_mcp.store import RepAIStore
from repai_mcp.timeutil import utc_now

# --------------------------------------------------------------------------- #
# sample_workout_inputs
# --------------------------------------------------------------------------- #
class WorkoutSample(BaseModel):
    session_id: str
    user_tag: str | None
    date: str
    raw_text: str


class WorkoutSamplesResult(BaseModel):
    count: int
    samples: list[WorkoutSample]


def build_workout_samples(
    sessions: list[dict],
    user_tags: dict[str, str],
    *,
    limit: int,
) -> WorkoutSamplesResult:
    samples: list[WorkoutSample] = []
    for s in sessions:
        raw = (s.get("raw_text") or "").strip()
        if not raw:
            continue
        samples.append(
            WorkoutSample(
                session_id=s["id"],
                user_tag=user_tags.get(s.get("user_id")),
                date=s["date"],
                raw_text=raw,
            )
        )
        if len(samples) >= limit:
            break
    return WorkoutSamplesResult(count=len(samples), samples=samples)


def sample_workout_inputs(
    store: RepAIStore,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    user_tag: str | None = None,
    limit: int = 20,
) -> WorkoutSamplesResult:
    """Return recent samples of users' raw workout text with context metadata.

    Filter by ISO date range (``start_date``/``end_date``), an optional
    ``user_tag``, and ``limit``. Useful for eyeballing how users actually phrase
    their logged workouts. Raises UserNotFoundError if user_tag is unknown.
    """
    user_id = None
    if user_tag:
        user_id = store.resolve_user_by_tag(user_tag).id

    sessions = store.list_workout_input_samples(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        limit=limit,
    )

    user_ids = list({s["user_id"] for s in sessions if s.get("user_id")})
    profiles = store.list_profiles_by_ids(user_ids)
    user_tags = {p["id"]: p["user_tag"] for p in profiles}

    return build_workout_samples(sessions, user_tags, limit=limit)


# --------------------------------------------------------------------------- #
# describe_user_base
# --------------------------------------------------------------------------- #
class UserBaseSummary(BaseModel):
    lookback_days: int
    total_users: int
    active_users: int
    signals: TrainingSignals
    goal_distribution: list[CategoryShare]
    experience_level_breakdown: list[CategoryShare]
    synthesis: str | None = None
    llm_note: str | None = None


def compute_user_base_summary(
    profiles: list[dict],
    sessions: list[dict],
    *,
    lookback_days: int,
) -> UserBaseSummary:
    non_guest = [p for p in profiles if not p.get("is_guest")]
    active_ids = {s.get("user_id") for s in sessions if s.get("user_id")}
    active = [p for p in non_guest if p["id"] in active_ids]

    signals = compute_training_signals(flatten_exercise_entries(sessions))

    return UserBaseSummary(
        lookback_days=lookback_days,
        total_users=len(non_guest),
        active_users=len(active),
        signals=signals,
        goal_distribution=categorical_distribution(
            goal for p in active for goal in (p.get("goals") or [])
        ),
        experience_level_breakdown=categorical_distribution(
            p.get("experience_level") for p in active
        ),
    )


def _attach_synthesis(
    summary: UserBaseSummary, llm: LLMClient | None
) -> UserBaseSummary:
    if llm is None:
        summary.llm_note = LLM_DISABLED_NOTE
        return summary
    try:
        payload = summary.model_dump(exclude={"synthesis", "llm_note"})
        summary.synthesis = synthesize_user_base(llm, payload)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never fail
        summary.llm_note = f"LLM cohort synthesis failed: {exc}"
    return summary


def describe_user_base(
    store: RepAIStore,
    *,
    lookback_days: int = 90,
    llm: LLMClient | None = None,
) -> UserBaseSummary:
    """Cohort-level behavioural aggregates across active (non-guest) users.

    Aggregates muscle group mix, top exercises, compound/isolation ratio,
    equipment breakdown, average reps, plus goal and experience-level
    distributions over users who logged a workout within ``lookback_days``. When
    ``llm`` is provided, a single LLM call synthesises the cohort into prose;
    otherwise structured signals are returned with a note.
    """
    cutoff = (utc_now() - timedelta(days=lookback_days)).isoformat()

    summary = compute_user_base_summary(
        store.list_profiles_for_user_base(),
        store.list_user_base_workout_sessions(cutoff),
        lookback_days=lookback_days,
    )
    return _attach_synthesis(summary, llm)
