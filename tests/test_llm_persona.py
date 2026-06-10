from repai_mcp.llm.persona import (
    LLM_DISABLED_NOTE,
    classify_persona,
    synthesize_user_base,
)
from repai_mcp.queries.signals import TrainingSignals
from repai_mcp.tools.cohort import _attach_synthesis, UserBaseSummary
from repai_mcp.tools.investigate import _attach_persona, UserDigest


class FakeLLM:
    def __init__(self, response: str):
        self._response = response
        self.calls: list[dict] = []

    @property
    def model(self) -> str:
        return "fake/model"

    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> str:
        self.calls.append({"system": system, "user": user})
        return self._response


def empty_signals() -> TrainingSignals:
    return TrainingSignals(
        total_exercises=1,
        total_sets=3,
        avg_reps=5.0,
        compound_ratio=1.0,
        muscle_group_distribution=[],
        type_breakdown=[],
        equipment_breakdown=[],
        top_exercises=[],
    )


def test_classify_persona_parses_json_with_code_fence():
    llm = FakeLLM(
        '```json\n{"persona": "powerlifting-leaning", "confidence": 0.9, '
        '"rationale": "Low reps, compound heavy.", '
        '"signals_considered": ["compound_ratio", "avg_reps"]}\n```'
    )
    result = classify_persona(
        llm, empty_signals(), goals=["gain_strength"], experience_level="advanced"
    )
    assert result.persona == "powerlifting-leaning"
    assert result.confidence == 0.9
    assert result.signals_considered == ["compound_ratio", "avg_reps"]
    assert result.model == "fake/model"


def test_synthesize_user_base_returns_prose():
    llm = FakeLLM("Mostly strength-focused intermediate lifters.")
    out = synthesize_user_base(llm, {"active_users": 10})
    assert "strength-focused" in out
    assert len(llm.calls) == 1


def sample_digest() -> UserDigest:
    from repai_mcp.tools.investigate import build_user_digest
    from datetime import datetime, timezone

    profile = {
        "id": "u1", "user_tag": "sam", "display_name": "Sam",
        "experience_level": "advanced", "goals": ["gain_strength"],
        "commitment_frequency": "4_times",
    }
    return build_user_digest(
        profile, [], 0, [], [], None,
        now=datetime(2026, 6, 10, tzinfo=timezone.utc),
    )


def test_attach_persona_disabled_without_client():
    digest = _attach_persona(sample_digest(), None)
    assert digest.persona is None
    assert digest.llm_note == LLM_DISABLED_NOTE


def test_attach_persona_with_client():
    llm = FakeLLM(
        '{"persona": "general-fitness", "confidence": 0.5, '
        '"rationale": "Sparse data.", "signals_considered": []}'
    )
    digest = _attach_persona(sample_digest(), llm)
    assert digest.persona.persona == "general-fitness"
    assert digest.llm_note is None


def test_attach_persona_degrades_on_error():
    llm = FakeLLM("not json")
    digest = _attach_persona(sample_digest(), llm)
    assert digest.persona is None
    assert "failed" in digest.llm_note


def sample_summary() -> UserBaseSummary:
    return UserBaseSummary(
        lookback_days=90,
        total_users=5,
        active_users=3,
        signals=empty_signals(),
        goal_distribution=[],
        experience_level_breakdown=[],
    )


def test_attach_synthesis_disabled_without_client():
    summary = _attach_synthesis(sample_summary(), None)
    assert summary.synthesis is None
    assert summary.llm_note == LLM_DISABLED_NOTE


def test_attach_synthesis_with_client():
    llm = FakeLLM("A mix of strength and hypertrophy lifters.")
    summary = _attach_synthesis(sample_summary(), llm)
    assert summary.synthesis == "A mix of strength and hypertrophy lifters."
    assert summary.llm_note is None
