from __future__ import annotations

from uk_wages import robustness


def test_robustness_sign_flipped_delegates_to_shared_sign_flip(monkeypatch) -> None:
    calls: list[tuple[float, float]] = []

    def fake_sign_flip(baseline: float, candidate: float) -> bool:
        calls.append((baseline, candidate))
        return True

    monkeypatch.setattr(robustness, "_sign_flip", fake_sign_flip)

    assert robustness.sign_flipped(1.0, 2.0)
    assert calls == [(1.0, 2.0)]
