import pytest

from repai_mcp.queries.users import UserNotFoundError, UserRef, resolve_user_by_tag
from repai_mcp.store import InMemoryRepAIStore


def test_resolve_user_by_tag_returns_ref():
    store = InMemoryRepAIStore(
        profiles=[{"id": "u1", "user_tag": "lifter_sam", "display_name": "Sam"}]
    )
    ref = resolve_user_by_tag(store, "lifter_sam")
    assert isinstance(ref, UserRef)
    assert ref.id == "u1"
    assert ref.user_tag == "lifter_sam"


def test_resolve_user_by_tag_not_found():
    with pytest.raises(UserNotFoundError, match="ghost"):
        resolve_user_by_tag(InMemoryRepAIStore(), "ghost")
