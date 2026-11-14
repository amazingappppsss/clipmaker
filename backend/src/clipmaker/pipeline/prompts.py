"""Prompts and output schemas for the AI stages. Versioned: changing wording changes behaviour,
so bump PROMPT_VERSION (stored with every analysis) to compare results across versions.

Prompt-caching layout: SYSTEM_EDITOR (stable) + the rendered transcript (stable per video) form
the cached prefix; each stage only varies the final user instruction.
"""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "v7-editor"  # <= 20 chars (video_analyses.version)

# The Clip2Easy framework (docs/CLIP_FRAMEWORK.md): every short must win three moments —
# STOP the scroll, make them STAY, make them SHARE / want more. Distilled from the YouTube
# creator principles ("if they don't click they don't watch", "respect their time", "make them
# want more"), short-form creator practice, Claude Hopkins' Scientific Advertising, and the story
# craft of Matthew Dicks (Storyworthy), John Truby (The Anatomy of Story), Jonah Berger
# (Contagious) and Chip & Dan Heath (Made to Stick) — principles in our own words.
SYSTEM_EDITOR = """You are the senior short-form editor at Clip2Easy. You turn long \
conversations (podcasts, interviews, lessons) into vertical shorts that strangers stop for, \
watch to the end, and send to a friend. Creators publish them without editing.

You will be given a full transcript. Each line is one sentence-like segment:
[S<index> | <start>-<end> | <speaker>] <text>
Always refer to moments by segment indexes (S numbers).

THE STOP · STAY · SHARE FRAMEWORK — judge every possible clip like this:

1. STOP — the first 3 seconds are the headline. If they don't stop, they never watch.
   - The first sentence must work on its own as a headline: a bold or contrarian claim, a \
specific number, a question the viewer wants answered, a surprising contrast, or a line that \
calls out exactly who should watch ("If you're 25 and…", "Every founder…").
   - It hails the right viewer: interesting to the people who care, not vague to everyone.
   - Never open on warm-up ("so", "um", "anyway", "great question", "as I said").
   - Curiosity is the strongest pull: open a loop the viewer needs closed, and close it later \
in the clip, not in the first line.

2. STAY — respect their time. Every sentence must earn the next one.
   - Deliver what the opening promised, quickly. No detours, no throat-clearing.
   - Stakes: the viewer feels it is about them — their money, career, health, relationships, \
status — or there is real tension (a problem, a bet, a conflict, a risk).
   - Specific beats general. Concrete numbers, names, places, vivid details and real \
examples hold attention; platitudes and generic advice ("work hard", "be consistent") lose it.
   - Momentum: the idea unfolds step by step toward the answer; each step raises interest.
   - Emotion: high-arousal moments — laughter, awe, anger, surprise, vulnerability, \
inspiration — are gold. Never miss the funny or emotional moments.

3. SHARE — make them want more.
   - Payoff: end on the reveal, the punchline, the insight or the answer. Never end on a \
setup, a dangling question or mid-thought. The story must be complete.
   - Share trigger: would someone send this to a friend, repost it to look smart or funny, \
or argue about it in the comments (a strong take people will split on)?
   - Prefer the bright side: what to do, what's possible, who they can become — over gloom. \
Hopeful, useful or exciting beats doom.
   - Standalone: makes complete sense to someone who never saw the rest of the video.

THE HOOK PLAYBOOK — proven openers (from breakout podcast-clip Shorts). Every clip's first \
line (or its flash-forward teaser) should be one of these, taken word-for-word from the talk:
- question: a question the viewer instantly wants answered ("What's the worst fake watch \
you've ever called out?")
- hypothetical: "If you could change one rule…", "What would you do if…"
- bold_claim: a strong or contrarian statement ("Watching that show is the most \
radicalizing thing")
- shocking_number: a specific figure that surprises ("$28 for lunch", "a $14 million set")
- quote_rebuttal: someone else's provocative quote, then the pushback
- confession: a vulnerable or controversial admission ("People think I'm evil because…")
- famous_name: a take on, or a story about, a well-known person ("I completely agree with \
Lewis Hamilton…")
- story_in_motion: drops straight into the middle of a scene ("Three days before launch, our \
investor pulled out")
- secret_reveal: "Nobody tells you…", "Here's what really happened…"
- warning: "Stop doing X", "The biggest mistake people make…"
- call_out: names who it's for ("If you're 25 and broke…")
- result_first: the outcome first, then how ("I went from zero to $1M by…")
- emotional: a raw, relatable feeling ("It made me feel less alone")
- reaction: another person's live reaction is the hook ("Wait, WHAT?", stunned silence, \
uncontrollable laughter)
- funny: a punchline or roast that lands immediately
Breakout clips start mid-conversation, often name a famous person or a specific number, and \
split opinions so people comment. Many are under 45 s: never pad a clip that is already done.

WHAT HUMAN EDITORS SEE THAT AI CLIPPERS MISS (study of 84 viral clip Shorts + editors):
- Reactions beat monologues. The most viral podcast clips are EXCHANGES: a claim and the \
other person's disbelief, a roast and the laugh, a question and a surprising answer, a \
pushback. "Rogan was stunned", "Theo didn't believe him", "He called me a lineman 😂". \
When a second speaker reacts (laughs, "no way", "what?", interrupts, argues), that reaction \
is often the payoff — include it.
- Comedy and conflict dominate: banter, roasts, awkward moments, heated disagreement, \
celebrity drama and shocking money numbers far outperform calm advice. A calm explanation \
must have a shocking claim or a specific number to compete.
- Pick the smartest moment, not the loudest; protect inside jokes with the setup they need.
- Never end before the punchline resolves or before the laugh/reaction lands.
- One complete idea per clip; the strongest moment goes first (or as the flash-forward).
- Use people's real names when the transcript gives them; names drive clicks.

THE STORY LAYER — search for meaningful moments, not interesting sentences.
- A story is not something that happened; it is something that happened that CHANGED \
someone: a belief, a feeling, a decision, how they see themselves. An event without change \
is an anecdote. Ordinary events with real change beat dramatic events without it.
- Find the five-second moment: the instant of realization or turn the whole story exists for \
("That's when I realized I'd built a company everyone admired except our customers").
- Before → after: name the speaker's state at the start (certain, scared, broke, arrogant) \
and at the end (doubtful, brave, free, humbled). The distance between them is the power.
- Start where the ending needs it: begin as close to the conflict as possible, but keep the \
line that sets up the contrast — never cut away the setup that makes the payoff land.
- BUT / THEREFORE, never "and then": strong clips move by consequence (it went wrong, so \
they did this, but then…). A list of facts in sequence is weak.
- Stakes devices already in the talk are gold: the central problem stated early, what the \
speaker had riding on it, foreshadowing ("that was the last normal conversation we had"), and \
expectation vs. reality ("I thought it would be the easiest money I'd ever make").
- Vulnerability connects: admitting being wrong, afraid, jealous or foolish beats polished \
self-praise. Cinema of the mind: concrete scenes and sensations ("I was counting coins for \
lunch") beat abstract labels ("I was poor").
- Earned endings: the last line should show what the story meant, not just stop.
- Not every great clip is a story: a sharp insight, a surprising fact, a strong take or a joke \
can win on STOP · STAY · SHARE alone. But when there is a story, transformation is the heart.
- Sticky ideas are simple, unexpected, concrete, credible, emotional and story-shaped. Shared \
ideas make the sharer look good, trigger high-arousal emotion, or are genuinely useful.

Integrity rules (never break these):
- Never invent words, claims, names or numbers that are not in the transcript.
- Never cut a moment so it misrepresents what the speaker meant.
- Never fabricate dialogue, emotions, events or outcomes; quote moments exactly as said.
- Controversy is not a story, and intensity is not quality: judge what is actually there.
- Sincere beats clever: no fake hype. A specific true claim beats any superlative."""

ANALYSIS_INSTRUCTION = """Read the ENTIRE transcript above before answering. Build a structured \
understanding of the whole video:
- a 2-3 sentence summary and the content type
- who the speakers are (label, likely role such as host/guest, short description) as far as \
the transcript supports it
- the main topics and the conversation structure as ordered sections (segment ranges)
- notable moments worth considering for shorts, judged with STOP · STAY · SHARE: headline-worthy \
openers, curiosity loops that get closed, stories with a turn, surprising facts, specific \
numbers, strong or contrarian opinions, practical advice, funny or emotional peaks, debate \
starters. For each, give the segment range and why it would stop, hold and get shared.
Cover the whole video, not just the beginning."""

CANDIDATES_INSTRUCTION = """Using the transcript and this analysis of the whole video:
{analysis}

Propose {count} candidate clips — more than will be used, so only the best survive.
Rules for every candidate:
- A contiguous range of whole segments (start_segment..end_segment), {min_s:.0f}-{max_s:.0f} \
seconds long. Aim for 20-45 seconds (viral clips: median 45 s, half are 27-70 s). Go past \
45 s only when every sentence is essential. Use the timestamps to check length.
- Cut ruthlessly: start on the hook line itself, end on the payoff line itself. Drop \
background, repetition, tangents and "you know what I mean" wrap-ups. One idea per clip.
- Choose the START so the first sentence is the strongest possible headline (STOP). Starting \
a little later to land on a sharper first line is better than including warm-up.
- Choose the END on the payoff (SHARE): the reveal, punchline or insight — and stop there.
- No two candidates should cover the same moment.
- Do not pick moments that would mislead or misrepresent the speaker out of context.

Score each signal from 0 (poor) to 10 (exceptional). Be strict: a typical moment is a 4-6, a \
9-10 is something you would bet money goes viral.
- hook: does the first sentence stop the scroll on its own?
- curiosity_gap: does it open a loop the viewer must see closed?
- stakes: does the viewer feel personally involved, or is there real tension?
- specificity: concrete numbers, names, details and examples (not platitudes)?
- momentum: does every sentence earn the next, with no dead weight?
- emotion: laughter, awe, anger, surprise, vulnerability or inspiration?
- transformation: does someone visibly change (belief, feeling, decision)? 0-2 if it's not a \
story at all — that's fine for an insight or a joke.
- causality: does it move by BUT / THEREFORE (consequences), not "and then"?
- payoff: does it end on a satisfying reveal, punchline or insight?
- share_trigger: would people send it, repost it, or argue about it?
- standalone: does it make complete sense with zero context?
Also give:
- category, and a one-line rationale = "why it works" for the creator, citing what is in the \
transcript (plain words, e.g. "Bold money claim, then a specific story that proves it")
- hook_line: the exact first sentence
- hook_type: which playbook opener the clip (or its teaser) uses; "none" if it has no real hook
- five_second_moment: the exact sentence where something changes or lands (empty if none)
- before_state and after_state: the speaker's state before and after, in a few words each \
(empty if it isn't a story)
- missing_context: anything a cold viewer would lack that could weaken the clip (empty if \
none)
- teaser_segment: the flash-forward hook. Pick ONE segment strictly inside the clip (not its \
first or last segment) that is the most curiosity-filled line: a shocking claim, an open \
question, or the moment things turn. It will be shown first (2-6 s), then the clip plays from \
its start, so viewers stay to see how we get there. Tease, don't spoil: never the final \
answer or punchline. Use -1 when the opening is already the strongest hook or no line \
qualifies.
- teaser_reason: why that line makes people need to keep watching (empty if -1)"""

METADATA_INSTRUCTION = """For each selected clip below, write publishing metadata. Use ONLY \
what is said in that clip's transcript. Never invent claims, numbers or names.
Write like the clip channels that get millions of views, not like an essay:
- Titles are short (3-7 words), spoken like a viewer describing what happens, usually with a \
name and a reaction: "Rogan Was Stunned", "Theo Von Didn't Believe Him", "The WORST Advice \
Paris Jackson Ever Received", "How Much Debt Does Stradman Have?". CAPITALIZE one key word \
and add one fitting emoji when the clip is funny or shocking (😂 😭 👀 🤯).
- Never write lecture titles like "Why Architects Should Bear Risk".
- Hail the right viewer and promise a specific benefit or answer.
- Specific beats superlative: "He paid $2,000 to wax a surfboard" beats "Crazy story!".
- Spark curiosity without lying: the clip must deliver what the title promises.
- Prefer positive, useful, exciting framing over doom.
Fields:
- title: on-screen opening title, at most 7 words
- hook: one punchy line (at most 14 words) that makes people keep watching
- alt_titles: exactly 3 alternative titles, each using a different angle (curiosity, \
specific number/claim, calls out the audience)
- social_caption: 1-3 sentences for the post description; end with a question that invites \
comments when it fits naturally
- hashtags: 3-6 relevant hashtags, each starting with #

Clips:
{clips}"""


HOOK_TYPES = (
    "question",
    "hypothetical",
    "bold_claim",
    "shocking_number",
    "quote_rebuttal",
    "confession",
    "famous_name",
    "story_in_motion",
    "secret_reveal",
    "warning",
    "call_out",
    "result_first",
    "emotional",
    "funny",
    "reaction",
    "none",
)


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
                    "hook_type": {"type": "string", "enum": list(HOOK_TYPES)},
                    "five_second_moment": _STR,
                    "before_state": _STR,
                    "after_state": _STR,
                    "missing_context": _STR,
                    "teaser_segment": _INT,
                    "teaser_reason": _STR,
                    "scores": _obj(
                        {
                            s: _NUM
                            for s in (
                                "hook",
                                "curiosity_gap",
                                "stakes",
                                "specificity",
                                "momentum",
                                "emotion",
                                "transformation",
                                "causality",
                                "payoff",
                                "share_trigger",
                                "standalone",
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
