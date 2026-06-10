"""create_ops_note: persist an internal operator note linked to a user."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from repai_mcp.store import RepAIStore


class OpsNote(BaseModel):
    id: str
    user_id: str
    user_tag: str
    note: str
    created_at: str
    metadata: dict[str, Any]


def create_ops_note(
    store: RepAIStore,
    *,
    user_tag: str,
    note: str,
    metadata: dict[str, Any] | None = None,
) -> OpsNote:
    """Validate the user exists, insert the note, return the stored record.

    Raises UserNotFoundError if user_tag does not match a profile.
    """
    text = note.strip()
    if not text:
        raise ValueError("note must not be empty.")

    user = store.resolve_user_by_tag(user_tag)

    row = store.insert_ops_note(
        user_id=user.id,
        note=text,
        metadata=metadata or {},
    )

    return OpsNote(
        id=row["id"],
        user_id=row["user_id"],
        user_tag=user.user_tag,
        note=row["note"],
        created_at=row["created_at"],
        metadata=row.get("metadata") or {},
    )
