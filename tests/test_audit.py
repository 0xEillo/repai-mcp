import json

import pytest

from repai_mcp.audit import AuditLogger


@pytest.fixture
def logger(tmp_path):
    return AuditLogger(tmp_path / "nested" / "audit.jsonl", mode="demo")


def read_entries(logger):
    return [
        json.loads(line)
        for line in logger.path.read_text().splitlines()
    ]


def test_record_appends_jsonl_entry(logger):
    logger.record(
        tool="health_check",
        arguments={"limit": 5},
        duration_ms=12.345,
        status="ok",
    )
    logger.record(
        tool="health_check",
        arguments={},
        duration_ms=1.0,
        status="ok",
    )

    entries = read_entries(logger)
    assert len(entries) == 2
    entry = entries[0]
    assert entry["tool"] == "health_check"
    assert entry["arguments"] == {"limit": 5}
    assert entry["mode"] == "demo"
    assert entry["duration_ms"] == 12.35
    assert entry["status"] == "ok"
    assert "timestamp" in entry
    assert "error" not in entry


def test_audited_wrapper_records_success(logger):
    @logger.audited
    def my_tool(value: int) -> int:
        return value * 2

    assert my_tool(value=21) == 42

    [entry] = read_entries(logger)
    assert entry["tool"] == "my_tool"
    assert entry["arguments"] == {"value": 21}
    assert entry["status"] == "ok"


def test_audited_wrapper_records_failure_and_reraises(logger):
    @logger.audited
    def broken_tool() -> None:
        raise RuntimeError("supabase exploded")

    with pytest.raises(RuntimeError, match="supabase exploded"):
        broken_tool()

    [entry] = read_entries(logger)
    assert entry["status"] == "error"
    assert entry["error"] == "supabase exploded"
