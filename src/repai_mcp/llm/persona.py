"""LLM persona/synthesis logic built on top of the structured signals.

Pure-ish helpers that take an LLM client plus already-computed signals and
return typed synthesis. Kept separate from the OpenRouter transport so tests can
inject a fake client, and from the tools so the SQL slices stay LLM-free.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel

from repai_mcp.queries.signals import TrainingSignals

LLM_DISABLED_NOTE = (
    "LLM synthesis disabled: set OPENROUTER_API_KEY to enable. "
    "Structured signals are returned as-is."
)


class LLMClient(Protocol):
    @property
    def model(self) -> str: ...

    def complete(
        self, *, system: str, user: str, temperature: float = ...
    ) -> str: ...


class PersonaClassification(BaseModel):
    persona: str
    confidence: float
    rationale: str
    signals_considered: list[str]
    model: str


_PERSONA_SYSTEM = (
    "You are a fitness analytics assistant for Rep AI, an AI workout tracker. "
    "Classify a single user's training persona using ONLY the provided "
    "behavioural signals. Choose exactly one persona from: powerlifting-leaning, "
    "bodybuilding-leaning, cardio-focused, general-fitness. Respond with ONLY a "
    "JSON object with keys: persona (string), confidence (float 0-1), rationale "
    "(one sentence), signals_considered (array of short strings naming the "
    "signals that drove your decision). Do not invent data."
)

_USERBASE_SYSTEM = (
    "You are a product analyst for Rep AI, an AI workout tracker. Given "
    "cohort-level behavioural aggregates, write a concise 2-4 sentence answer "
    "to 'What kinds of gym goers use Rep AI?'. Ground every claim in the "
    "provided numbers; do not invent data. Plain prose, no markdown."
)


def _extract_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned


def classify_persona(
    client: LLMClient,
    signals: TrainingSignals,
    *,
    goals: list[str],
    experience_level: str | None,
) -> PersonaClassification:
    """Ask the LLM to classify a training persona from behavioural signals."""
    user = json.dumps(
        {
            "goals": goals,
            "experience_level": experience_level,
            "signals": signals.model_dump(),
        },
        default=str,
    )
    raw = client.complete(system=_PERSONA_SYSTEM, user=user)
    data = json.loads(_extract_json(raw))
    return PersonaClassification(
        persona=str(data["persona"]),
        confidence=float(data.get("confidence", 0.0)),
        rationale=str(data.get("rationale", "")),
        signals_considered=[str(s) for s in data.get("signals_considered", [])],
        model=client.model,
    )


def synthesize_user_base(client: LLMClient, payload: dict[str, Any]) -> str:
    """Single LLM call summarising the cohort aggregates into prose."""
    raw = client.complete(
        system=_USERBASE_SYSTEM, user=json.dumps(payload, default=str)
    )
    return raw.strip()
