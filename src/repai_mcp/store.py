"""Rep AI data-access port and Supabase adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel
from supabase import Client, create_client

from repai_mcp.config import Config


class UserNotFoundError(LookupError):
    """Raised when a user_tag does not match any profile."""

    def __init__(self, user_tag: str) -> None:
        super().__init__(f"No user found with user_tag {user_tag!r}.")
        self.user_tag = user_tag


class UserRef(BaseModel):
    id: str
    user_tag: str
    display_name: str | None = None


class RepAIStore(Protocol):
    """Data-access port used by MCP tools."""

    def ping(self) -> None: ...

    def resolve_user_by_tag(self, user_tag: str) -> UserRef: ...

    def get_profile_by_user_tag(self, user_tag: str) -> dict | None: ...

    def list_user_workout_sessions(self, user_id: str) -> list[dict]: ...

    def count_user_ai_chat_usage(self, user_id: str) -> int: ...

    def list_user_coach_messages(self, user_id: str) -> list[dict]: ...

    def list_user_email_events(self, user_id: str) -> list[dict]: ...

    def get_user_strength_snapshot(self, user_id: str) -> dict | None: ...

    def list_profiles_for_commitment(self) -> list[dict]: ...

    def list_workout_sessions_since(self, cutoff: str) -> list[dict]: ...

    def list_recent_trial_profiles(self, trial_cutoff: str) -> list[dict]: ...

    def list_workout_sessions_for_users(self, user_ids: list[str]) -> list[dict]: ...

    def list_stuck_workout_sessions(self) -> list[dict]: ...

    def list_profiles_by_ids(self, user_ids: list[str]) -> list[dict]: ...

    def list_coach_messages_since(self, cutoff: str) -> list[dict]: ...

    def list_workout_input_samples(
        self,
        *,
        start_date: str | None,
        end_date: str | None,
        user_id: str | None,
        limit: int,
    ) -> list[dict]: ...

    def list_profiles_for_user_base(self) -> list[dict]: ...

    def list_user_base_workout_sessions(self, cutoff: str) -> list[dict]: ...

    def insert_ops_note(
        self,
        *,
        user_id: str,
        note: str,
        metadata: dict[str, Any],
    ) -> dict: ...


_INVESTIGATE_SESSION_SELECT = (
    "id, date, raw_text, "
    "workout_exercises(exercises(name, muscle_group, type, equipment), "
    "sets(reps))"
)
_COHORT_SELECT = (
    "id, user_id, date, "
    "workout_exercises(exercise_id, "
    "exercises(name, muscle_group, type, equipment), sets(reps))"
)


def create_repai_store(config: Config) -> RepAIStore:
    return SupabaseRepAIStore(
        create_client(config.supabase_url, config.supabase_service_role_key)
    )


class SupabaseRepAIStore:
    """Supabase-backed implementation of the Rep AI store port."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def ping(self) -> None:
        self._client.table("profiles").select(
            "id", count="exact", head=True
        ).limit(1).execute()

    def resolve_user_by_tag(self, user_tag: str) -> UserRef:
        profile = self.get_profile_by_user_tag(user_tag)
        if profile is None:
            raise UserNotFoundError(user_tag)
        return UserRef(
            id=profile["id"],
            user_tag=profile["user_tag"],
            display_name=profile.get("display_name"),
        )

    def get_profile_by_user_tag(self, user_tag: str) -> dict | None:
        rows = (
            self._client.table("profiles")
            .select("*")
            .eq("user_tag", user_tag)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def list_user_workout_sessions(self, user_id: str) -> list[dict]:
        return (
            self._client.table("workout_sessions")
            .select(_INVESTIGATE_SESSION_SELECT)
            .eq("user_id", user_id)
            .eq("is_processing", False)
            .order("date", desc=True)
            .execute()
            .data
            or []
        )

    def count_user_ai_chat_usage(self, user_id: str) -> int:
        rows = (
            self._client.table("ai_chat_usage")
            .select("id")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )
        return len(rows)

    def list_user_coach_messages(self, user_id: str) -> list[dict]:
        return (
            self._client.table("proactive_coach_messages")
            .select("trigger_type, consumed_at")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )

    def list_user_email_events(self, user_id: str) -> list[dict]:
        return (
            self._client.table("email_automation_events")
            .select("email_type")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )

    def get_user_strength_snapshot(self, user_id: str) -> dict | None:
        rows = (
            self._client.table("onboarding_strength_snapshots")
            .select("working_weight_kg, reps, estimated_1rm_kg, exercises(name)")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def list_profiles_for_commitment(self) -> list[dict]:
        return (
            self._client.table("profiles")
            .select("id, user_tag, display_name, commitment, commitment_frequency")
            .execute()
            .data
            or []
        )

    def list_workout_sessions_since(self, cutoff: str) -> list[dict]:
        return (
            self._client.table("workout_sessions")
            .select("user_id, date")
            .eq("is_processing", False)
            .gte("date", cutoff)
            .execute()
            .data
            or []
        )

    def list_recent_trial_profiles(self, trial_cutoff: str) -> list[dict]:
        return (
            self._client.table("profiles")
            .select("id, user_tag, display_name, trial_start_date")
            .gte("trial_start_date", trial_cutoff)
            .execute()
            .data
            or []
        )

    def list_workout_sessions_for_users(self, user_ids: list[str]) -> list[dict]:
        if not user_ids:
            return []
        return (
            self._client.table("workout_sessions")
            .select("user_id, date")
            .eq("is_processing", False)
            .in_("user_id", user_ids)
            .execute()
            .data
            or []
        )

    def list_stuck_workout_sessions(self) -> list[dict]:
        return (
            self._client.table("workout_sessions")
            .select("id, user_id, created_at, raw_text")
            .eq("is_processing", True)
            .execute()
            .data
            or []
        )

    def list_profiles_by_ids(self, user_ids: list[str]) -> list[dict]:
        if not user_ids:
            return []
        return (
            self._client.table("profiles")
            .select("id, user_tag")
            .in_("id", user_ids)
            .execute()
            .data
            or []
        )

    def list_coach_messages_since(self, cutoff: str) -> list[dict]:
        return (
            self._client.table("proactive_coach_messages")
            .select("trigger_type, created_at, consumed_at")
            .gte("created_at", cutoff)
            .execute()
            .data
            or []
        )

    def list_workout_input_samples(
        self,
        *,
        start_date: str | None,
        end_date: str | None,
        user_id: str | None,
        limit: int,
    ) -> list[dict]:
        query = (
            self._client.table("workout_sessions")
            .select("id, user_id, date, raw_text")
            .not_.is_("raw_text", "null")
            .order("date", desc=True)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
        return query.limit(limit).execute().data or []

    def list_profiles_for_user_base(self) -> list[dict]:
        return (
            self._client.table("profiles")
            .select("id, goals, experience_level, is_guest")
            .execute()
            .data
            or []
        )

    def list_user_base_workout_sessions(self, cutoff: str) -> list[dict]:
        return (
            self._client.table("workout_sessions")
            .select(_COHORT_SELECT)
            .eq("is_processing", False)
            .gte("date", cutoff)
            .execute()
            .data
            or []
        )

    def insert_ops_note(
        self,
        *,
        user_id: str,
        note: str,
        metadata: dict[str, Any],
    ) -> dict:
        rows = (
            self._client.table("ops_notes")
            .insert({"user_id": user_id, "note": note, "metadata": metadata})
            .execute()
            .data
            or []
        )
        if not rows:
            raise RuntimeError("Insert into ops_notes returned no row.")
        return rows[0]


@dataclass
class InMemoryRepAIStore:
    """Small test adapter for exercising tools through their public interface."""

    profiles: list[dict] = field(default_factory=list)
    workout_sessions: list[dict] = field(default_factory=list)
    ai_chat_usage: list[dict] = field(default_factory=list)
    proactive_coach_messages: list[dict] = field(default_factory=list)
    email_automation_events: list[dict] = field(default_factory=list)
    onboarding_strength_snapshots: list[dict] = field(default_factory=list)
    ops_notes: list[dict] = field(default_factory=list)
    ping_error: Exception | None = None

    def ping(self) -> None:
        if self.ping_error:
            raise self.ping_error

    def resolve_user_by_tag(self, user_tag: str) -> UserRef:
        profile = self.get_profile_by_user_tag(user_tag)
        if profile is None:
            raise UserNotFoundError(user_tag)
        return UserRef(
            id=profile["id"],
            user_tag=profile["user_tag"],
            display_name=profile.get("display_name"),
        )

    def get_profile_by_user_tag(self, user_tag: str) -> dict | None:
        return next(
            (p for p in self.profiles if p.get("user_tag") == user_tag),
            None,
        )

    def list_user_workout_sessions(self, user_id: str) -> list[dict]:
        rows = [
            s
            for s in self.workout_sessions
            if s.get("user_id") == user_id and not s.get("is_processing", False)
        ]
        return sorted(rows, key=lambda s: s.get("date") or "", reverse=True)

    def count_user_ai_chat_usage(self, user_id: str) -> int:
        return len(
            [r for r in self.ai_chat_usage if r.get("user_id") == user_id]
        )

    def list_user_coach_messages(self, user_id: str) -> list[dict]:
        return [
            m
            for m in self.proactive_coach_messages
            if m.get("user_id") == user_id
        ]

    def list_user_email_events(self, user_id: str) -> list[dict]:
        return [
            e
            for e in self.email_automation_events
            if e.get("user_id") == user_id
        ]

    def get_user_strength_snapshot(self, user_id: str) -> dict | None:
        return next(
            (
                r
                for r in self.onboarding_strength_snapshots
                if r.get("user_id") == user_id
            ),
            None,
        )

    def list_profiles_for_commitment(self) -> list[dict]:
        return self.profiles

    def list_workout_sessions_since(self, cutoff: str) -> list[dict]:
        return [
            s
            for s in self.workout_sessions
            if not s.get("is_processing", False) and (s.get("date") or "") >= cutoff
        ]

    def list_recent_trial_profiles(self, trial_cutoff: str) -> list[dict]:
        return [
            p
            for p in self.profiles
            if p.get("trial_start_date")
            and p["trial_start_date"] >= trial_cutoff
        ]

    def list_workout_sessions_for_users(self, user_ids: list[str]) -> list[dict]:
        ids = set(user_ids)
        return [
            s
            for s in self.workout_sessions
            if s.get("user_id") in ids and not s.get("is_processing", False)
        ]

    def list_stuck_workout_sessions(self) -> list[dict]:
        return [s for s in self.workout_sessions if s.get("is_processing") is True]

    def list_profiles_by_ids(self, user_ids: list[str]) -> list[dict]:
        ids = set(user_ids)
        return [p for p in self.profiles if p.get("id") in ids]

    def list_coach_messages_since(self, cutoff: str) -> list[dict]:
        return [
            m
            for m in self.proactive_coach_messages
            if (m.get("created_at") or "") >= cutoff
        ]

    def list_workout_input_samples(
        self,
        *,
        start_date: str | None,
        end_date: str | None,
        user_id: str | None,
        limit: int,
    ) -> list[dict]:
        rows = [
            s
            for s in self.workout_sessions
            if s.get("raw_text") is not None
            and (user_id is None or s.get("user_id") == user_id)
            and (start_date is None or (s.get("date") or "") >= start_date)
            and (end_date is None or (s.get("date") or "") <= end_date)
        ]
        rows.sort(key=lambda s: s.get("date") or "", reverse=True)
        return rows[:limit]

    def list_profiles_for_user_base(self) -> list[dict]:
        return self.profiles

    def list_user_base_workout_sessions(self, cutoff: str) -> list[dict]:
        return [
            s
            for s in self.workout_sessions
            if not s.get("is_processing", False) and (s.get("date") or "") >= cutoff
        ]

    def insert_ops_note(
        self,
        *,
        user_id: str,
        note: str,
        metadata: dict[str, Any],
    ) -> dict:
        row = {
            "id": f"note-{len(self.ops_notes) + 1}",
            "user_id": user_id,
            "note": note,
            "created_at": "",
            "metadata": metadata,
        }
        self.ops_notes.append(row)
        return row
