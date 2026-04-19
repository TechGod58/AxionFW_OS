from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    checkpoint_threshold: float
    rollback_threshold: float
    halt_threshold: float
    recovered_threshold: float


PROFILES = {
    "conservative": PolicyProfile(
        name="conservative",
        checkpoint_threshold=0.28,
        rollback_threshold=0.46,
        halt_threshold=0.72,
        recovered_threshold=0.25,
    ),
    "balanced": PolicyProfile(
        name="balanced",
        checkpoint_threshold=0.34,
        rollback_threshold=0.55,
        halt_threshold=0.78,
        recovered_threshold=0.30,
    ),
    "aggressive": PolicyProfile(
        name="aggressive",
        checkpoint_threshold=0.42,
        rollback_threshold=0.64,
        halt_threshold=0.84,
        recovered_threshold=0.36,
    ),
}


def get_profile(name: str | None) -> PolicyProfile:
    if not name:
        return PROFILES["balanced"]
    return PROFILES.get(name, PROFILES["balanced"])
