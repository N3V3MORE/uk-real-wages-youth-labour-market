from __future__ import annotations

import re
from pathlib import Path

PUBLIC_FILES = [
    Path("README.md"),
    Path("reports/research_note.md"),
    Path("reports/policy_brief.md"),
    Path("reports/methodology.md"),
    Path("docs/reviewer_guide.md"),
    Path("outputs/evidence/final_claims.md"),
]


def _sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]


def _assert_no_unqualified_sentence(pattern: str, *, allowed_markers: tuple[str, ...]) -> None:
    offenders: list[str] = []
    regex = re.compile(pattern, flags=re.IGNORECASE)
    for path in PUBLIC_FILES:
        if not path.exists():
            continue
        for sentence in _sentences(path.read_text(encoding="utf-8")):
            if regex.search(sentence) and not any(
                marker.lower() in sentence.lower() for marker in allowed_markers
            ):
                offenders.append(f"{path}: {sentence}")
    assert offenders == []


def test_earn01_is_never_age_specific_evidence() -> None:
    _assert_no_unqualified_sentence(
        r"\bEARN01\b.*\bage-specific\b",
        allowed_markers=("not age-specific", "not use EARN01", "should not", "do not provide"),
    )


def test_rti_never_replaces_ashe() -> None:
    _assert_no_unqualified_sentence(
        r"\bRTI\b.*\b(replaces|replacement for|substitute for)\b.*\bASHE\b",
        allowed_markers=("does not", "not a replacement", "not an ASHE substitute"),
    )


def test_ashe_2026_age_specific_wages_are_not_claimed() -> None:
    _assert_no_unqualified_sentence(
        r"\bASHE 2026\b.*\bage-specific\b.*\bwage",
        allowed_markers=("does not", "do not", "not claim", "not because", "unless ASHE 2026"),
    )


def test_minimum_wage_is_not_causal_evidence_for_ashe() -> None:
    _assert_no_unqualified_sentence(
        r"\bminimum wage\b.*\b(caused|causes|causal|proof)\b.*\bASHE\b",
        allowed_markers=("not causal", "not as causal", "not causal proof", "not proof", "does not"),
    )


def test_decomposition_is_not_causal_proof() -> None:
    _assert_no_unqualified_sentence(
        r"\bdecomposition\b.*\b(causal|caused|causes|proves|proof)\b",
        allowed_markers=("not causal", "not a causal", "should not", "do not"),
    )


def test_18_21_clean_gain_or_loss_is_always_qualified() -> None:
    _assert_no_unqualified_sentence(
        r"\b18-21\b.*\bclearly became\b.*\b(better|worse)\b",
        allowed_markers=("does not support", "do not", "cannot", "not state"),
    )
