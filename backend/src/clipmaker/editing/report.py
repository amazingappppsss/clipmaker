"""A report card for a finished clip: the benchmark we have been editing without.

We have been changing the editor on instinct — tighten this, slow that — with nothing that
measures whether a clip got better. Deliberate practice fails in exactly two ways: no design,
and no feedback. The design is written down in docs/CLIP_FRAMEWORK.md. This is the feedback.

Every number here is computed from the render plan we already store: no AI call, no second
pass over the video. They are deliberately plain, measurable things an editor would notice —
how much silence is left, whether anything is still "um", whether the picture ever changes,
whether the clip opens mid-sentence — not a verdict on whether a clip is good. A score we
cannot check would be the same unproven number we criticise OpusClip for.

The targets come from the framework and from the 84-clip study behind it. They are starting
points, like the signal weights, and they are written here so that changing one is a decision
somebody makes on purpose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from clipmaker.editing.cuts import FILLERS

#: A gap longer than this, still in the finished clip, reads as dead air.
DEAD_AIR_GAP = 0.6
#: Above this fraction of the clip spent in dead air, it drags.
MAX_DEAD_AIR = 0.12
#: Conversational speech runs about 2.3-3.3 words a second. Outside that it rushes or crawls.
MIN_WORDS_PER_SECOND = 1.8
MAX_WORDS_PER_SECOND = 4.2
#: The framework asks for a visual change every 3-8 seconds.
MIN_SHOT_SECONDS = 3.0
MAX_SHOT_SECONDS = 12.0
#: Captions should be up for most of the clip; gaps are where attention goes.
MIN_CAPTION_COVERAGE = 0.75
#: The median breakout Short is 45s, the middle half 27-70s.
IDEAL_SECONDS = (18.0, 70.0)

_SENTENCE_END = re.compile(r"[.!?…]$")
_WEAK_OPENERS = frozenset({"so", "and", "but", "because", "which", "that", "then", "well"})


@dataclass(frozen=True, slots=True)
class Finding:
    """One thing worth knowing about a clip. `ok` False means it misses a target."""

    key: str
    value: float | str | None
    ok: bool
    note: str


def _words(plan: dict[str, Any]) -> list[tuple[str, float, float]]:
    out = []
    for row in plan.get("words") or []:
        if isinstance(row, list | tuple) and len(row) >= 3:
            out.append((str(row[0]), float(row[1]), float(row[2])))
    return out


def dead_air_ratio(words: list[tuple[str, float, float]], duration: float) -> float:
    """Fraction of the clip spent in gaps long enough to notice (pure)."""
    if duration <= 0 or len(words) < 2:
        return 0.0
    quiet = 0.0
    for (_, _, end), (_, start, _) in pairwise(words):
        gap = start - end
        if gap > DEAD_AIR_GAP:
            quiet += gap
    return round(quiet / duration, 3)


def caption_coverage(words: list[tuple[str, float, float]], duration: float) -> float:
    """Fraction of the clip with a word on screen (pure)."""
    if duration <= 0 or not words:
        return 0.0
    spoken = sum(max(0.0, end - start) for _, start, end in words)
    return round(min(1.0, spoken / duration), 3)


def shot_seconds(plan: dict[str, Any]) -> list[float]:
    """How long the framing holds still, per shot (pure)."""
    out = []
    for piece in plan.get("pieces") or []:
        if isinstance(piece, dict):
            length = float(piece.get("end", 0)) - float(piece.get("start", 0))
            if length > 0:
                out.append(round(length, 2))
    return out


def filler_left(words: list[tuple[str, float, float]]) -> list[str]:
    """Filler that survived the cut (pure). Should be empty."""
    return [
        text for text, _, _ in words if "".join(c for c in text.lower() if c.isalnum()) in FILLERS
    ]


def opens_cold(words: list[tuple[str, float, float]]) -> bool:
    """Whether the clip opens on a word that needs the sentence before it (pure)."""
    if not words:
        return True
    first = words[0][0].strip().lower().strip(".,!?;:")
    return first in _WEAK_OPENERS


def ends_mid_sentence(words: list[tuple[str, float, float]]) -> bool:
    """Whether the last word leaves the sentence hanging (pure)."""
    if not words:
        return True
    return not _SENTENCE_END.search(words[-1][0].strip())


def report(plan: dict[str, Any]) -> list[Finding]:
    """Measure one clip against the framework's targets (pure)."""
    words = _words(plan)
    duration = float(plan.get("duration") or 0.0)
    shots = shot_seconds(plan)
    findings: list[Finding] = []

    length_ok = IDEAL_SECONDS[0] <= duration <= IDEAL_SECONDS[1]
    findings.append(
        Finding(
            "length",
            round(duration, 1),
            length_ok,
            "in the range breakout Shorts live in"
            if length_ok
            else f"outside {IDEAL_SECONDS[0]:.0f}-{IDEAL_SECONDS[1]:.0f}s",
        )
    )

    dead = dead_air_ratio(words, duration)
    findings.append(
        Finding(
            "dead_air",
            dead,
            dead <= MAX_DEAD_AIR,
            "tight" if dead <= MAX_DEAD_AIR else f"{dead:.0%} of the clip is silence",
        )
    )

    pace = round(len(words) / duration, 2) if duration > 0 else 0.0
    pace_ok = MIN_WORDS_PER_SECOND <= pace <= MAX_WORDS_PER_SECOND
    findings.append(
        Finding(
            "pace",
            pace,
            pace_ok,
            "natural" if pace_ok else ("rushed" if pace > MAX_WORDS_PER_SECOND else "slow"),
        )
    )

    left = filler_left(words)
    findings.append(
        Finding(
            "filler",
            len(left),
            not left,
            "none left" if not left else f"still says {', '.join(sorted(set(left))[:3])}",
        )
    )

    coverage = caption_coverage(words, duration)
    findings.append(
        Finding(
            "captions",
            coverage,
            coverage >= MIN_CAPTION_COVERAGE,
            "on screen throughout"
            if coverage >= MIN_CAPTION_COVERAGE
            else f"blank for {1 - coverage:.0%} of the clip",
        )
    )

    longest = max(shots) if shots else duration
    shots_ok = bool(shots) and longest <= MAX_SHOT_SECONDS
    findings.append(
        Finding(
            "framing",
            round(longest, 1),
            shots_ok,
            f"{len(shots)} shots, longest {longest:.0f}s"
            if shots_ok
            else f"holds one frame for {longest:.0f}s",
        )
    )

    cold = opens_cold(words)
    findings.append(
        Finding(
            "opening",
            words[0][0] if words else None,
            not cold,
            "stands on its own" if not cold else "opens on a word that needs what came before",
        )
    )

    hanging = ends_mid_sentence(words)
    findings.append(
        Finding(
            "ending",
            words[-1][0] if words else None,
            not hanging,
            "lands on a finished sentence" if not hanging else "ends mid-sentence",
        )
    )
    return findings


def summarise(findings: list[Finding]) -> dict[str, Any]:
    """The report card as stored and shown: counts, and what missed."""
    missed = [f for f in findings if not f.ok]
    return {
        "checks": len(findings),
        "passed": len(findings) - len(missed),
        "missed": [{"key": f.key, "note": f.note} for f in missed],
        "values": {f.key: f.value for f in findings},
    }
