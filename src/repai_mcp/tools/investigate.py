"""investigate_user: full structured digest for a single user.

Pulls a user's onboarding intent, workout history, AI chat volume, proactive
coach engagement, lifecycle emails, onboarding strength snapshot, and computed
training behavioural signals into one typed model suitable for agent reasoning.

No LLM here — persona classification is layered on in issue 06. As with the
other tools, Supabase fetching is kept separate from the pure ``build_user_digest``
compute seam so the latter can be unit-tested with fixtures.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from repai_mcp.llm.persona import (
    LLM_DISABLED_NOTE,
    LLMClient,
    PersonaClassification,
    classify_persona,
)
from repai_mcp.queries.commitment import weekly_target_from_profile
from repai_mcp.queries.signals import (
    TrainingSignals,
    compute_training_signals,
    flatten_exercise_entries,
)
from repai_mcp.store import RepAIStore, UserNotFoundError
from repai_mcp.timeutil import parse_timestamp, utc_now

_PREVIEW_CHARS = 140
_RECENT_LIMIT = 5

def _preview(text: str | None) -> str | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if len(cleaned) > _PREVIEW_CHARS:
        return cleaned[:_PREVIEW_CHARS].rstrip() + "…"
    return cleaned


class ProfileSummary(BaseModel):
    user_tag: str
    display_name: str | None
    gender: str | None
    age: int | None
    experience_level: str | None
    coach: str | None
    is_guest: bool
    overall_strength_score: int | None
    overall_strength_level: str | None


class OnboardingIntent(BaseModel):
    goals: list[str]
    commitment: list[str] | None
    commitment_frequency: str | None
    weekly_target: int | None


class RecentWorkout(BaseModel):
    session_id: str
    date: str
    raw_text_preview: str | None
    exercise_count: int


class WorkoutSummary(BaseModel):
    total_sessions: int
    first_session_date: str | None
    last_session_date: str | None
    days_since_last_workout: int | None
    recent: list[RecentWorkout]


class CoachEngagement(BaseModel):
    sent: int
    consumed: int
    consumption_rate: float


class EmailTypeCount(BaseModel):
    email_type: str
    count: int


class EmailActivity(BaseModel):
    total: int
    by_type: list[EmailTypeCount]


class StrengthSnapshot(BaseModel):
    exercise: str | None
    working_weight_kg: float
    reps: int
    estimated_1rm_kg: float


class UserDigest(BaseModel):
    profile: ProfileSummary
    intent: OnboardingIntent
    workouts: WorkoutSummary
    ai_chat_usage_count: int
    coach_engagement: CoachEngagement
    email_activity: EmailActivity
    strength_snapshot: StrengthSnapshot | None
    signals: TrainingSignals
    persona: PersonaClassification | None = None
    llm_note: str | None = None


def _build_workout_summary(
    sessions: list[dict], *, now: datetime
) -> WorkoutSummary:
    dates = [parse_timestamp(s["date"]) for s in sessions if s.get("date")]
    last = max(dates) if dates else None
    first = min(dates) if dates else None

    recent = [
        RecentWorkout(
            session_id=s["id"],
            date=s["date"],
            raw_text_preview=_preview(s.get("raw_text")),
            exercise_count=len(s.get("workout_exercises") or []),
        )
        for s in sessions[:_RECENT_LIMIT]
    ]

    return WorkoutSummary(
        total_sessions=len(sessions),
        first_session_date=first.isoformat() if first else None,
        last_session_date=last.isoformat() if last else None,
        days_since_last_workout=(now - last).days if last else None,
        recent=recent,
    )


def _build_coach_engagement(messages: list[dict]) -> CoachEngagement:
    sent = len(messages)
    consumed = sum(1 for m in messages if m.get("consumed_at"))
    rate = round(consumed / sent, 3) if sent else 0.0
    return CoachEngagement(sent=sent, consumed=consumed, consumption_rate=rate)


def _build_email_activity(events: list[dict]) -> EmailActivity:
    counts: dict[str, int] = {}
    for e in events:
        etype = e.get("email_type") or "unknown"
        counts[etype] = counts.get(etype, 0) + 1
    by_type = [
        EmailTypeCount(email_type=t, count=c)
        for t, c in sorted(counts.items())
    ]
    return EmailActivity(total=len(events), by_type=by_type)


def _build_strength_snapshot(row: dict | None) -> StrengthSnapshot | None:
    if not row:
        return None
    exercise = (row.get("exercises") or {}).get("name")
    return StrengthSnapshot(
        exercise=exercise,
        working_weight_kg=row["working_weight_kg"],
        reps=row["reps"],
        estimated_1rm_kg=row["estimated_1rm_kg"],
    )


def build_user_digest(
    profile: dict,
    sessions: list[dict],
    chat_count: int,
    coach_messages: list[dict],
    email_events: list[dict],
    strength_row: dict | None,
    *,
    now: datetime,
) -> UserDigest:
    """Assemble the typed digest from already-fetched rows.

    ``sessions`` are expected newest-first with nested workout_exercises/sets.
    """
    return UserDigest(
        profile=ProfileSummary(
            user_tag=profile["user_tag"],
            display_name=profile.get("display_name"),
            gender=profile.get("gender"),
            age=profile.get("age"),
            experience_level=profile.get("experience_level"),
            coach=profile.get("coach"),
            is_guest=bool(profile.get("is_guest")),
            overall_strength_score=profile.get("overall_strength_score"),
            overall_strength_level=profile.get("overall_strength_level"),
        ),
        intent=OnboardingIntent(
            goals=profile.get("goals") or [],
            commitment=profile.get("commitment"),
            commitment_frequency=profile.get("commitment_frequency"),
            weekly_target=weekly_target_from_profile(
                profile.get("commitment"), profile.get("commitment_frequency")
            ),
        ),
        workouts=_build_workout_summary(sessions, now=now),
        ai_chat_usage_count=chat_count,
        coach_engagement=_build_coach_engagement(coach_messages),
        email_activity=_build_email_activity(email_events),
        strength_snapshot=_build_strength_snapshot(strength_row),
        signals=compute_training_signals(flatten_exercise_entries(sessions)),
    )


def _attach_persona(digest: UserDigest, llm: LLMClient | None) -> UserDigest:
    if llm is None:
        digest.llm_note = LLM_DISABLED_NOTE
        return digest
    try:
        digest.persona = classify_persona(
            llm,
            digest.signals,
            goals=digest.intent.goals,
            experience_level=digest.profile.experience_level,
        )
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, never fail
        digest.llm_note = f"LLM persona classification failed: {exc}"
    return digest


def investigate_user(
    store: RepAIStore, *, user_tag: str, llm: LLMClient | None = None
) -> UserDigest:
    """Return a complete structured digest for one user, looked up by user_tag.

    Includes onboarding intent, workout history and behavioural training
    signals, AI chat volume, coach-message engagement, lifecycle email events,
    and the onboarding strength snapshot. When ``llm`` is provided an LLM persona
    classification is attached; otherwise signals are returned with a note.
    Raises UserNotFoundError if no profile matches user_tag.
    """
    profile = store.get_profile_by_user_tag(user_tag)
    if profile is None:
        raise UserNotFoundError(user_tag)
    user_id = profile["id"]

    digest = build_user_digest(
        profile,
        store.list_user_workout_sessions(user_id),
        store.count_user_ai_chat_usage(user_id),
        store.list_user_coach_messages(user_id),
        store.list_user_email_events(user_id),
        store.get_user_strength_snapshot(user_id),
        now=utc_now(),
    )
    return _attach_persona(digest, llm)
