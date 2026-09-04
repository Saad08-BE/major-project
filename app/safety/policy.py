"""Small, explicit safety guardrails used before retrieval or generation."""

from __future__ import annotations

from dataclasses import dataclass
import re


_PATIENT_RECORD_PATTERNS = (
    r"\b(find|show|look up|search|retrieve)\b.*\b(patient|patient id|record)\b",
    r"\b(patient|patient id|record)\b.*\b(find|show|look up|search|retrieve)\b",
)
_URGENT_PATTERNS = (
    r"\b(chest pain|difficulty breathing|can'?t breathe|unconscious|severe bleeding)\b",
)


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    normalized_question: str
    user_message: str | None = None
    urgent: bool = False


def healthcare_disclaimer() -> str:
    return (
        "This tool provides educational information from local sources and is not a medical diagnosis. "
        "For urgent or severe symptoms, seek immediate help from a qualified healthcare professional or emergency service."
    )


def validate_question(question: str) -> SafetyDecision:
    """Reject empty and patient-record requests; flag urgent wording for the UI."""
    normalized = " ".join(question.split())
    if not normalized:
        return SafetyDecision(False, "", "Enter a healthcare question or symptoms to continue.")
    lowered = normalized.lower()
    if any(re.search(pattern, lowered) for pattern in _PATIENT_RECORD_PATTERNS):
        return SafetyDecision(
            False,
            normalized,
            "Patient-record search is not available. Ask a general, de-identified healthcare question instead.",
        )
    urgent = any(re.search(pattern, lowered) for pattern in _URGENT_PATTERNS)
    return SafetyDecision(True, normalized, urgent=urgent)

