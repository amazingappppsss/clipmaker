"""Animated captions as an ASS subtitle file (burned in by FFmpeg/libass). Pure, unit-tested.

The look viral clips use: big bold uppercase words centred low, 1-3 words at a time; the word
being spoken pops and lights up in lime; key words (numbers, money, names) stay highlighted
so the eye catches them. The clip's hook title sits at the top for the first seconds.
"""

from __future__ import annotations

import re

from clipmaker.providers.transcription.base import Word

PLAY_W, PLAY_H = 1080, 1920
LIME = "&H002EFFC8&"  # #C8FF2E in ASS (alpha, blue, green, red)
WHITE = "&H00FFFFFF&"
MAX_WORDS_PER_CHUNK = 3
MAX_CHARS_PER_CHUNK = 18
CHUNK_BREAK_GAP = 0.35  # a pause this long starts a new caption
#: Words that cannot end a caption line. Breaking after them leaves a fragment dangling —
#: "OF THE CRAZY", "BECAUSE THEY ARE" — which reads as a glitch rather than as speech.
#: They are carried into the next line instead.
HANGING_WORDS = frozenset(
    {
        # Articles and determiners.
        "a",
        "an",
        "the",
        "this",
        "these",
        "those",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        # Conjunctions and subordinators.
        "and",
        "but",
        "or",
        "nor",
        "so",
        "yet",
        "because",
        "as",
        "than",
        "if",
        "when",
        "while",
        "that",
        # Prepositions.
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "from",
        "into",
        "onto",
        "about",
        "over",
        "under",
        # Auxiliaries: "they are" is not a line, "they are watching" is. Pronouns are
        # deliberately absent — "I promise you" ends perfectly well.
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "am",
        "will",
        "would",
        "can",
        "could",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
    }
)
TITLE_SECONDS = 3.0
CAPTION_HOLD = 0.12  # how long the last word of a line stays up before the next line

_SENTENCE_END = re.compile(r"[.!?…]$")
_NUMBERISH = re.compile(r"[\d$€£%]")
_QUOTES = "\"'()\u201c\u201d\u2018\u2019"  # straight and curly quotes, brackets


def _ts(seconds: float) -> str:
    """ASS timestamp h:mm:ss.cc"""
    cs = max(0, round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def _strip_emoji(text: str) -> str:
    """Burned-in text can't draw emoji (the font has none): drop them, keep everything else."""
    kept = "".join(ch for ch in text if ord(ch) < 0x2190 or 0x2E80 <= ord(ch) < 0x1F000)
    return " ".join(kept.split())


def _clean(text: str) -> str:
    """Caption form of a word: uppercase, trailing commas/periods dropped (kept: ? ! numbers)."""
    return _escape(text.strip().rstrip(",.;:").upper())


def payoff_words(words: list[Word], moment: str | None) -> set[int]:
    """Indexes of the words that make up the five-second moment (pure).

    The framework says to light up the payoff, and we already know where it is — the model
    quotes it for every clip. Lighting only numbers and names leaves the one line the clip
    exists for looking like every other line.
    """
    if not moment:
        return set()
    wanted = [_bare_word(t) for t in moment.split()]
    wanted = [t for t in wanted if t]
    if len(wanted) < 2:
        return set()
    bare = [_bare_word(w.text) for w in words]
    for start in range(len(bare) - len(wanted) + 1):
        if bare[start : start + len(wanted)] == wanted:
            return set(range(start, start + len(wanted)))
    # The quote rarely survives filler removal intact, so fall back to the longest run of it
    # that does appear. A partial hit still lands on the right line.
    for size in range(len(wanted) - 1, 2, -1):
        for offset in range(len(wanted) - size + 1):
            needle = wanted[offset : offset + size]
            for start in range(len(bare) - size + 1):
                if bare[start : start + size] == needle:
                    return set(range(start, start + size))
    return set()


def _bare_word(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum())


def is_keyword(word: Word, previous: Word | None) -> bool:
    """Numbers and money always; capitalised words that don't start a sentence (names)."""
    text = word.text.strip()
    if _NUMBERISH.search(text):
        return True
    starts_sentence = previous is None or bool(_SENTENCE_END.search(previous.text.strip()))
    core = text.strip(_QUOTES)
    return (
        bool(core[:1].isupper()) and not starts_sentence and core.upper() != "I" and len(core) > 1
    )


def _hangs(word: Word) -> bool:
    """Whether a line ending on this word would leave the phrase dangling (pure)."""
    bare = "".join(c for c in word.text.lower() if c.isalnum())
    return bool(bare) and bare in HANGING_WORDS and not _SENTENCE_END.search(word.text.strip())


def chunk_words(words: list[Word]) -> list[list[Word]]:
    """Group words into short caption lines (1-3 words, breaking on pauses and sentences)."""
    chunks: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        if cur:
            prev = cur[-1]
            chars = sum(len(x.text) + 1 for x in cur) + len(w.text)
            wants_break = (
                len(cur) >= MAX_WORDS_PER_CHUNK
                or chars > MAX_CHARS_PER_CHUNK
                or w.start - prev.end > CHUNK_BREAK_GAP
                or _SENTENCE_END.search(prev.text.strip())
                or w.speaker != prev.speaker
            )
            # A real pause or a new speaker is a real break, whatever the last word was. A
            # break only because the line got long is moved earlier instead of orphaning the
            # word that leads into the next phrase.
            forced = (
                w.start - prev.end > CHUNK_BREAK_GAP
                or bool(_SENTENCE_END.search(prev.text.strip()))
                or w.speaker != prev.speaker
            )
            carry = 0
            while wants_break and not forced and len(cur) - carry > 1 and _hangs(cur[-1 - carry]):
                carry += 1
            if carry:
                # "none of | the crazy" rather than "none of the | crazy": every trailing
                # word that leads into the next phrase moves with it, not just the last one.
                chunks.append(cur[:-carry])
                cur = cur[-carry:]
            elif wants_break:
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def _header(font: str) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PLAY_W}
PlayResY: {PLAY_H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, \
Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, \
Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},96,{WHITE},{WHITE},&H00000000&,&H80000000&,-1,0,0,0,100,100,1,0,1,7,3,\
2,60,60,560,1
Style: Title,{font},64,&H00000000&,&H00000000&,{LIME},{LIME},-1,0,0,0,100,100,0,0,3,20,0,\
8,90,90,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_ass(
    words: list[Word],
    *,
    title: str | None = None,
    title_seconds: float = TITLE_SECONDS,
    font: str = "Montserrat Black",
    window: tuple[float, float] | None = None,
    moment: str | None = None,
) -> str:
    """ASS document for words already on the output timeline.

    `moment` is the clip's five-second moment; those words are lit like keywords, because the
    payoff is the line the clip exists for.

    `window` limits it to one rendered piece: only captions overlapping [start, end) are kept,
    and their times are shifted so the piece starts at zero. That lets captions be burned in
    while each piece is encoded, so the finished video is never re-encoded a second time.
    """
    w0, w1 = window if window else (0.0, float("inf"))

    def emit(start: float, end: float, body: str) -> str | None:
        if end <= w0 or start >= w1:
            return None
        return f"{_ts(max(start, w0) - w0)},{_ts(min(end, w1) - w0)},{body}"

    lines = [_header(font)]
    if title:
        event = emit(
            0.0,
            title_seconds,
            f"Title,,0,0,0,,{{\\fad(150,250)}}{_escape(_strip_emoji(title).upper())}",
        )
        if event:
            lines.append(f"Dialogue: 1,{event}")
    previous: Word | None = None
    payoff = payoff_words(words, moment)
    keywords: dict[int, bool] = {}
    for i, w in enumerate(words):
        keywords[i] = i in payoff or is_keyword(w, previous)
        previous = w
    # Build every caption event first, then make sure none overlaps the next one. Two events
    # alive at the same instant are drawn on top of each other (libass stacks them), which is
    # the "glitchy doubled subtitle" look.
    events: list[tuple[float, float, str]] = []
    index = 0
    for chunk in chunk_words(words):
        ids = list(range(index, index + len(chunk)))
        index += len(chunk)
        for j, active in enumerate(chunk):
            parts = []
            for k, w in zip(ids, chunk, strict=True):
                text = _clean(w.text)
                if w is active:
                    parts.append(f"{{\\c{LIME}\\fscx112\\fscy112}}{text}{{\\r}}")
                elif keywords[k]:
                    parts.append(f"{{\\c{LIME}}}{text}{{\\r}}")
                else:
                    parts.append(text)
            pop = "{\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)}" if j == 0 else ""
            natural = chunk[j + 1].start if j + 1 < len(chunk) else active.end + CAPTION_HOLD
            events.append((active.start, max(natural, active.start + 0.05), pop + " ".join(parts)))

    for i in range(len(events) - 1):
        begin, finish, body = events[i]
        events[i] = (begin, min(finish, events[i + 1][0]), body)
    for begin, finish, body in events:
        if finish <= begin:
            continue
        event = emit(begin, finish, f"Caption,,0,0,0,,{body}")
        if event:
            lines.append(f"Dialogue: 0,{event}")

    return "\n".join(lines) + "\n"
