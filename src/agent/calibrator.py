"""Domain-specific calibration offsets.

Based on paper Table 2 (Karkar & Chopra, 2025):
  - Geopolitics: 84–88% accuracy → minimal adjustment needed
  - Finance:     44–56% accuracy → pull towards 0.5 (regression to base rate)

These are additive offsets applied to the raw LLM probability.
Calibration is intentionally conservative — the offset pulls the forecast
toward the domain's empirical base rate rather than over-correcting.
"""

from __future__ import annotations

# (domain, condition) → additive offset to apply to raw probability [−1, 1]
# Positive = push toward YES; negative = push toward NO; 0 = no change.
_OFFSETS: dict[tuple[str, str], float] = {
    # Finance: regress toward 0.5 (paper shows LLM overconfidence in direction)
    ("Finance", "raw"):  0.0,   # no systematic directional bias observed
    ("Finance", "news"): 0.0,
    # Geopolitics: slight upward adjustment for YES (base rate skew in Metaculus data)
    ("Geopolitics", "raw"):  0.02,
    ("Geopolitics", "news"): 0.01,
    # Crypto: high volatility → widen CI, nudge toward 0.5
    ("Crypto", "raw"):  0.0,
    ("Crypto", "news"): 0.0,
}

# Domain-level shrinkage toward 0.5 for low-accuracy domains
_SHRINKAGE: dict[str, float] = {
    "Finance": 0.12,    # strongest shrinkage
    "Crypto":  0.08,
    "Sports":  0.04,
    "Politics": 0.02,
    "Geopolitics": 0.0,
    "Technology": 0.03,
    "Entertainment": 0.05,
}


def calibrate(raw_prob: float, domain: str, condition: str) -> float:
    """Return a calibrated probability in [0.0, 1.0].

    Applies:
    1. Domain-level shrinkage toward 0.5.
    2. Condition-specific additive offset.
    """
    shrinkage = _SHRINKAGE.get(domain, 0.0)
    shrunk = raw_prob + shrinkage * (0.5 - raw_prob)  # pulls toward 0.5

    offset = _OFFSETS.get((domain, condition), 0.0)
    calibrated = shrunk + offset

    return max(0.01, min(0.99, calibrated))
