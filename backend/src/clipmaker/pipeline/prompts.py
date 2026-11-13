"""Prompts and output schemas for the AI stages. Versioned: changing wording changes behaviour,
so bump PROMPT_VERSION (stored with every analysis) to compare results across versions.

Prompt-caching layout: SYSTEM_EDITOR (stable) + the rendered transcript (stable per video) form
the cached prefix; each stage only varies the final user instruction.
"""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "v1"

SYSTEM_EDITOR = """You are the senior short-form video editor at ClipMaker. You turn long \
conversations (podcasts, interviews, lessons) into vertical shorts that viewers watch to the end \
and creators publish without editing.

You will be given a full transcript. Each line is one sentence-like segment:
[S<index> | <start>-<end> | <speaker>] <text>
Always refer to moments by segment indexes (S numbers). Never invent words, claims, names or \
numbers that are not in the transcript. A clip must make sense to someone who never saw the \
rest of the video, and must not misrepresent what the speaker meant."""

ANALYSIS_INSTRUCTION = """Read the ENTIRE transcript above before answering. Build a structured \
understanding of the whole video:
- a 2-3 sentence summary and the content type
- who the speakers are (label, likely role such as host/guest, short description) as far as \
the transcript supports it
- the main topics and the conversation structure as ordered sections (segment ranges)
- notable moments worth considering for shorts: stories, surprising facts or insights, strong \
opinions, practical advice, funny or emotional moments, clear explanations, good questions with \
complete answers. For each, give the segment range and why it stands out.
Cover the whole video, not just the beginning."""

CANDIDATES_INSTRUCTION = """Using the transcript and this analysis of the whole video:
{analysis}

Propose {count} candidate clips — more than will be used, so the best can be chosen.
Rules for every candidate:
- It is a contiguous range of whole segments (start_segment..end_segment), roughly \
{min_s:.0f}-{max_s:.0f} seconds long (ideal 30-60s). Use the timestamps to check length.
- The first segment must hook immediately (no slow warm-up, no "so, um, anyway").
- It contains a complete idea: enough context to stand alone, and a satisfying payoff or \
conclusion at the end. Never end on a setup, a dangling question or mid-thought.
- No two candidates should cover the same moment.
- Do not pick moments that would mislead or misrepresent the speaker when cut out of context.
Score each signal from 0 (poor) to 10 (excellent), honestly — most moments are not a 9:
standalone_context, strong_opening, story_payoff, emotional_engagement, information_value, \
natural_ending.
Also give the category, a one-line rationale, and the exact sentence that works as the hook."""

METADATA_INSTRUCTION = """For each selected clip below, write publishing metadata. Use ONLY \
what is said in that clip's transcript. Never invent claims, numbers or names. Avoid generic \
clickbait; be specific to the clip.
- title: on-screen opening title, at most 7 words
- hook: one punchy line (at most 14 words) that makes people keep watching
- alt_titles: exactly 3 alternative titles
- social_caption: 1-3 sentences for the post description
- hashtags: 3-6 relevant hashtags, each starting with #

Clips:
{clips}"""


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties),
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}
_NUM = {"type": "number"}

ANALYSIS_SCHEMA = _obj(
    {
        "summary": _STR,
        "content_type": {
            "type": "string",
            "enum": ["podcast", "interview", "educational", "business", "gaming", "other"],
        },
        "speakers": {
            "type": "array",
            "items": _obj({"label": _STR, "role": _STR, "description": _STR}),
        },
        "topics": {"type": "array", "items": _STR},
        "sections": {
            "type": "array",
            "items": _obj(
                {"title": _STR, "start_segment": _INT, "end_segment": _INT, "summary": _STR}
            ),
        },
        "notable_moments": {
            "type": "array",
            "items": _obj({"start_segment": _INT, "end_segment": _INT, "kind": _STR, "why": _STR}),
        },
    }
)

CANDIDATES_SCHEMA = _obj(
    {
        "candidates": {
            "type": "array",
            "items": _obj(
                {
                    "start_segment": _INT,
                    "end_segment": _INT,
                    "category": {
                        "type": "string",
                        "enum": [
                            "story",
                            "surprising_fact",
                            "strong_opinion",
                            "educational",
                            "funny",
                            "emotional",
                            "controversial",
                            "practical_advice",
                            "q_and_a",
                        ],
                    },
                    "rationale": _STR,
                    "hook_line": _STR,
                    "scores": _obj(
                        {
                            s: _NUM
                            for s in (
                                "standalone_context",
                                "strong_opening",
                                "story_payoff",
                                "emotional_engagement",
                                "information_value",
                                "natural_ending",
                            )
                        }
                    ),
                }
            ),
        }
    }
)

METADATA_SCHEMA = _obj(
    {
        "clips": {
            "type": "array",
            "items": _obj(
                {
                    "clip_number": _INT,
                    "title": _STR,
                    "hook": _STR,
                    "alt_titles": {"type": "array", "items": _STR},
                    "social_caption": _STR,
                    "hashtags": {"type": "array", "items": _STR},
                }
            ),
        }
    }
)
