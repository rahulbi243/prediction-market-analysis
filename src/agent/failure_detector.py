"""Regex-based detector for the three failure modes identified in the paper.

Karkar & Chopra (2025) §4.3:
  1. Recency Bias         — over-weighting recent events/news
  2. Rumour Overweighting — treating unconfirmed sources as high-confidence
  3. Definition Drift     — ambiguous resolution criteria
"""

from __future__ import annotations

import re

# ── Pattern definitions ───────────────────────────────────────────────────────

_RECENCY_PATTERNS = [
    # "just / recently / yesterday ... suggests / indicates / shows"
    re.compile(
        r"\b(just|recent(?:ly)?|yesterday|last (?:week|day|hour)|breaking|latest)\b"
        r".{0,60}"
        r"\b(suggest|indicate|show|point|signal|confirm|reveal)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # "this week's news changes / shifts / updates"
    re.compile(
        r"\b(this week|today|overnight|as of (?:now|today|this morning))\b"
        r".{0,80}"
        r"\b(change|shift|update|alter|increase|decrease|raise|lower)\b",
        re.IGNORECASE | re.DOTALL,
    ),
]

_RUMOUR_PATTERNS = [
    re.compile(
        r"\b(rumou?r|unconfirmed|source says?|reportedly|alleged(?:ly)?|specul(?:ate|ation)|leak(?:ed)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(it is said|may have|might have|could have)\b"
        r".{0,40}"
        r"\b(suggest|indicate|imply|hint)\b",
        re.IGNORECASE | re.DOTALL,
    ),
]

_DEFINITION_DRIFT_PATTERNS = [
    re.compile(
        r"\b(could mean|might refer|ambiguous|unclear (?:whether|if|what)|assume[sd]? (?:it |this )?refers?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(what counts? as|resolution criteria|how (?:this|it) is defined|depends on (?:the )?definition)\b",
        re.IGNORECASE,
    ),
    # Ambiguous acronyms: two-or-more capital-letter sequences followed by "could/may mean"
    re.compile(
        r"\b[A-Z]{2,}\b.{0,40}\b(could|may|might)\b.{0,40}\b(mean|refer|indicate)\b",
        re.DOTALL,
    ),
]

_FAILURE_MODES: dict[str, list[re.Pattern]] = {
    "RecencyBias": _RECENCY_PATTERNS,
    "RumourOverweighting": _RUMOUR_PATTERNS,
    "DefinitionDrift": _DEFINITION_DRIFT_PATTERNS,
}


# ── Public API ────────────────────────────────────────────────────────────────

def detect_failure_modes(reasoning: str) -> list[str]:
    """Return a list of failure mode names detected in the reasoning text.

    Returns a subset of: ["RecencyBias", "RumourOverweighting", "DefinitionDrift"]
    """
    detected: list[str] = []
    for mode, patterns in _FAILURE_MODES.items():
        if any(p.search(reasoning) for p in patterns):
            detected.append(mode)
    return detected
