"""Retention and operational read tools.

Four founder-question tools that surface users and sessions needing attention:

- find_commitment_gaps: stated weekly target vs actual workout frequency
- find_trial_dropoff_risk: trial users who have gone quiet
- find_stuck_workout_sessions: workout parses stuck in processing
- summarize_coach_engagement: proactive coach messages sent vs consumed

Each tool is a thin fetch over Supabase plus a pure compute function. The
compute functions are the primary unit-test seam.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from repai_mcp.queries.commitment import weekly_target_from_profile
from repai_mcp.store import RepAIStore
from repai_mcp.timeutil import parse_timestamp, utc_now

_PREVIEW_CHARS = 140


# --------------------------------------------------------------------------- #
# find_commitment_gaps
# --------------------------------------------------------------------------- #
class CommitmentGap(BaseModel):
    user_tag: str
    display_name: str | None
    weekly_target: int
    workouts_in_window: int
    actual_per_week: float
    gap_per_week: float


class CommitmentGapsResult(BaseModel):
    lookback_days: int
    min_gap_per_week: float
    count: int
    users: list[CommitmentGap]


def compute_commitment_gaps(
    profiles: list[dict],
    sessions: list[dict],
    *,
    lookback_days: int,
    min_gap_per_week: float,
    limit: int,
) -> CommitmentGapsResult:
    counts: dict[str, int] = {}
    for s in sessions:
        uid = s.get("user_id")
        if uid is not None:
            counts[uid] = counts.get(uid, 0) + 1

    weeks = max(lookback_days / 7, 1e-9)
    gaps: list[CommitmentGap] = []
    for p in profiles:
        target = weekly_target_from_profile(
            p.get("commitment"), p.get("commitment_frequency")
        )
        if target is None:
            continue
        workouts = counts.get(p["id"], 0)
        actual = workouts / weeks
        gap = target - actual
        if gap >= min_gap_per_week:
            gaps.append(
                CommitmentGap(
                    user_tag=p["user_tag"],
                    display_name=p.get("display_name"),
                    weekly_target=target,
                    workouts_in_window=workouts,
                    actual_per_week=round(actual, 2),
                    gap_per_week=round(gap, 2),
                )
            )

    gaps.sort(key=lambda g: g.gap_per_week, reverse=True)
    return CommitmentGapsResult(
        lookback_days=lookback_days,
        min_gap_per_week=min_gap_per_week,
        count=len(gaps),
        users=gaps[:limit],
    )


def find_commitment_gaps(
    store: RepAIStore,
    *,
    lookback_days: int = 14,
    min_gap_per_week: float = 1.0,
    limit: int = 50,
) -> CommitmentGapsResult:
    """Users whose stated weekly commitment exceeds their actual workout
    frequency over the lookback window. Higher gap = further behind intent."""
    cutoff = (utc_now() - timedelta(days=lookback_days)).isoformat()

    return compute_commitment_gaps(
        store.list_profiles_for_commitment(),
        store.list_workout_sessions_since(cutoff),
        lookback_days=lookback_days,
        min_gap_per_week=min_gap_per_week,
        limit=limit,
    )


# --------------------------------------------------------------------------- #
# find_trial_dropoff_risk
# --------------------------------------------------------------------------- #
class TrialAtRiskUser(BaseModel):
    user_tag: str
    display_name: str | None
    trial_start_date: str
    days_since_trial_start: int
    workouts_since_trial_start: int
    days_since_last_workout: int | None


class TrialDropoffResult(BaseModel):
    trial_window_days: int
    inactive_days: int
    count: int
    users: list[TrialAtRiskUser]


def compute_trial_dropoff(
    profiles: list[dict],
    sessions: list[dict],
    *,
    now: datetime,
    trial_window_days: int,
    inactive_days: int,
    limit: int,
) -> TrialDropoffResult:
    by_user: dict[str, list[datetime]] = {}
    for s in sessions:
        uid = s.get("user_id")
        if uid is not None and s.get("date"):
            by_user.setdefault(uid, []).append(parse_timestamp(s["date"]))

    at_risk: list[TrialAtRiskUser] = []
    for p in profiles:
        raw_start = p.get("trial_start_date")
        if not raw_start:
            continue
        trial_start = parse_timestamp(raw_start)
        dates = [d for d in by_user.get(p["id"], []) if d >= trial_start]
        workouts = len(dates)
        last = max(dates) if dates else None
        days_since_last = (now - last).days if last else None

        is_quiet = days_since_last is None or days_since_last >= inactive_days
        if not is_quiet:
            continue

        at_risk.append(
            TrialAtRiskUser(
                user_tag=p["user_tag"],
                display_name=p.get("display_name"),
                trial_start_date=raw_start,
                days_since_trial_start=(now - trial_start).days,
                workouts_since_trial_start=workouts,
                days_since_last_workout=days_since_last,
            )
        )

    # Never-worked-out first, then longest gap since last workout.
    at_risk.sort(
        key=lambda u: (
            u.days_since_last_workout is not None,
            -(u.days_since_last_workout or 0),
        )
    )
    return TrialDropoffResult(
        trial_window_days=trial_window_days,
        inactive_days=inactive_days,
        count=len(at_risk),
        users=at_risk[:limit],
    )


def find_trial_dropoff_risk(
    store: RepAIStore,
    *,
    trial_window_days: int = 14,
    inactive_days: int = 5,
    limit: int = 50,
) -> TrialDropoffResult:
    """Users whose trial started within the window but who have logged no
    workouts in the last `inactive_days` (or none at all since trial start)."""
    now = utc_now()
    trial_cutoff = (now - timedelta(days=trial_window_days)).isoformat()

    profiles = store.list_recent_trial_profiles(trial_cutoff)
    user_ids = [p["id"] for p in profiles]
    sessions = store.list_workout_sessions_for_users(user_ids)
    return compute_trial_dropoff(
        profiles,
        sessions,
        now=now,
        trial_window_days=trial_window_days,
        inactive_days=inactive_days,
        limit=limit,
    )


# --------------------------------------------------------------------------- #
# find_stuck_workout_sessions
# --------------------------------------------------------------------------- #
class StuckSession(BaseModel):
    session_id: str
    user_tag: str | None
    created_at: str
    minutes_stuck: float
    raw_text_preview: str | None


class StuckSessionsResult(BaseModel):
    older_than_minutes: int
    count: int
    sessions: list[StuckSession]


def compute_stuck_sessions(
    sessions: list[dict],
    user_tags: dict[str, str],
    *,
    now: datetime,
    older_than_minutes: int,
    limit: int,
) -> StuckSessionsResult:
    stuck: list[StuckSession] = []
    for s in sessions:
        created_raw = s.get("created_at")
        if not created_raw:
            continue
        minutes = (now - parse_timestamp(created_raw)).total_seconds() / 60
        if minutes < older_than_minutes:
            continue
        preview = (s.get("raw_text") or "").strip() or None
        if preview and len(preview) > _PREVIEW_CHARS:
            preview = preview[:_PREVIEW_CHARS].rstrip() + "…"
        stuck.append(
            StuckSession(
                session_id=s["id"],
                user_tag=user_tags.get(s.get("user_id")),
                created_at=created_raw,
                minutes_stuck=round(minutes, 1),
                raw_text_preview=preview,
            )
        )

    stuck.sort(key=lambda s: s.minutes_stuck, reverse=True)
    return StuckSessionsResult(
        older_than_minutes=older_than_minutes,
        count=len(stuck),
        sessions=stuck[:limit],
    )


def find_stuck_workout_sessions(
    store: RepAIStore,
    *,
    older_than_minutes: int = 15,
    limit: int = 50,
) -> StuckSessionsResult:
    """Workout sessions stuck in `is_processing=true` for longer than the
    threshold — a signal of failed or abandoned AI workout parses."""
    now = utc_now()
    sessions = store.list_stuck_workout_sessions()
    user_ids = list({s["user_id"] for s in sessions if s.get("user_id")})
    profiles = store.list_profiles_by_ids(user_ids)
    user_tags = {p["id"]: p["user_tag"] for p in profiles}

    return compute_stuck_sessions(
        sessions,
        user_tags,
        now=now,
        older_than_minutes=older_than_minutes,
        limit=limit,
    )


# --------------------------------------------------------------------------- #
# summarize_coach_engagement
# --------------------------------------------------------------------------- #
class TriggerBreakdown(BaseModel):
    trigger_type: str
    sent: int
    consumed: int
    consumption_rate: float


class CoachEngagementResult(BaseModel):
    lookback_days: int
    total_sent: int
    total_consumed: int
    consumption_rate: float
    by_trigger: list[TriggerBreakdown]


def _rate(consumed: int, sent: int) -> float:
    return round(consumed / sent, 3) if sent else 0.0


def compute_coach_engagement(
    messages: list[dict],
    *,
    lookback_days: int,
) -> CoachEngagementResult:
    total_sent = len(messages)
    total_consumed = sum(1 for m in messages if m.get("consumed_at"))

    grouped: dict[str, dict[str, int]] = {}
    for m in messages:
        trigger = m.get("trigger_type") or "unknown"
        bucket = grouped.setdefault(trigger, {"sent": 0, "consumed": 0})
        bucket["sent"] += 1
        if m.get("consumed_at"):
            bucket["consumed"] += 1

    by_trigger = [
        TriggerBreakdown(
            trigger_type=trigger,
            sent=b["sent"],
            consumed=b["consumed"],
            consumption_rate=_rate(b["consumed"], b["sent"]),
        )
        for trigger, b in sorted(grouped.items())
    ]

    return CoachEngagementResult(
        lookback_days=lookback_days,
        total_sent=total_sent,
        total_consumed=total_consumed,
        consumption_rate=_rate(total_consumed, total_sent),
        by_trigger=by_trigger,
    )


def summarize_coach_engagement(
    store: RepAIStore,
    *,
    lookback_days: int = 30,
) -> CoachEngagementResult:
    """Proactive coach messages sent vs consumed over the lookback window,
    overall and broken down by trigger type."""
    cutoff = (utc_now() - timedelta(days=lookback_days)).isoformat()
    messages = store.list_coach_messages_since(cutoff)
    return compute_coach_engagement(messages, lookback_days=lookback_days)
