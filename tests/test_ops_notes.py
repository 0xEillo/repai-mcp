import pytest

from repai_mcp.queries.users import UserNotFoundError
from repai_mcp.store import InMemoryRepAIStore
from repai_mcp.tools.ops_notes import OpsNote, create_ops_note


PROFILE = {"id": "user-uuid", "user_tag": "lifter_sam", "display_name": "Sam"}


def test_create_ops_note_success():
    store = InMemoryRepAIStore(profiles=[PROFILE])

    result = create_ops_note(
        store,
        user_tag="lifter_sam",
        note="Checked their stuck session.",
        metadata={"source": "investigation"},
    )

    assert isinstance(result, OpsNote)
    assert result.id == "note-1"
    assert result.user_id == "user-uuid"
    assert result.user_tag == "lifter_sam"
    assert result.metadata == {"source": "investigation"}


def test_create_ops_note_unknown_user_raises():
    with pytest.raises(UserNotFoundError, match="missing_user"):
        create_ops_note(
            InMemoryRepAIStore(), user_tag="missing_user", note="hi"
        )


def test_create_ops_note_rejects_empty_note():
    store = InMemoryRepAIStore(profiles=[PROFILE])

    with pytest.raises(ValueError, match="must not be empty"):
        create_ops_note(store, user_tag="lifter_sam", note="   ")


def test_create_ops_note_trims_note_before_insert():
    store = InMemoryRepAIStore(profiles=[PROFILE])

    create_ops_note(store, user_tag="lifter_sam", note="  padded  ")

    assert store.ops_notes[0]["note"] == "padded"
    assert store.ops_notes[0]["metadata"] == {}
