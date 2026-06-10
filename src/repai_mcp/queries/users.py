"""Compatibility exports for user lookup types."""

from __future__ import annotations

from repai_mcp.store import RepAIStore, UserNotFoundError, UserRef


def resolve_user_by_tag(store: RepAIStore, user_tag: str) -> UserRef:
    return store.resolve_user_by_tag(user_tag)
