"""editing/captions.py — chunking, keyword emphasis, ASS output."""

from __future__ import annotations

import itertools

from clipmaker.editing.captions import LIME, _ts, build_ass, chunk_words, is_keyword
from clipmaker.providers.transcription.base import Word


def _words(text: str, start: float = 0.0, step: float = 0.3) -> list[Word]:
    return [Word(t, start + i * step, start + i * step + 0.25) for i, t in enumerate(text.split())]


def test_chunks_are_short_and_break_on_sentences() -> None:
    chunks = chunk_words(_words("I paid twenty grand. Then everything went completely wrong"))
    assert all(1 <= len(c) <= 3 for c in chunks)
    assert chunks[1][-1].text == "grand."  # sentence end closes the caption
    assert chunks[2][0].text == "Then"


def test_keywords_are_numbers_and_names() -> None:
    w = _words("I met Rick Ross and paid $28")
    assert is_keyword(w[3], w[2])  # Ross (name mid-sentence)
    assert is_keyword(w[6], w[5])  # $28
    assert not is_keyword(w[0], None)  # sentence start
    assert not is_keyword(w[1], w[0])


def test_ass_highlights_the_active_word_and_shows_the_title() -> None:
    doc = build_ass(_words("This changed my life"), title="He Quit Everything")
    assert "PlayResY: 1920" in doc
    assert "HE QUIT EVERYTHING" in doc
    events = [line for line in doc.splitlines() if line.startswith("Dialogue: 0")]
    assert len(events) == 4  # one event per spoken word
    assert all(LIME in e for e in events)


def test_text_is_escaped() -> None:
    doc = build_ass([Word("{evil}\\N", 0, 1)])
    assert (
        "{evil}" not in doc and "\\N" not in doc.split("[Events]")[1].split("Caption,,0,0,0,,")[1]
    )


def test_timestamps() -> None:
    assert _ts(0) == "0:00:00.00"
    assert _ts(61.257) == "0:01:01.26"


def test_title_drops_emoji_the_font_cannot_draw() -> None:
    doc = build_ass([], title="Rogan Was Stunned 😭")
    assert "ROGAN WAS STUNNED" in doc and "😭" not in doc


def test_caption_events_never_overlap() -> None:
    """Two captions alive at once get drawn on top of each other — the glitchy doubled look."""
    import re

    words = [
        Word("Great", 0.0, 0.3),
        Word("but", 0.35, 0.5),
        Word("I", 0.55, 0.6),  # sentence break here; next line starts almost immediately
        Word("don't", 0.62, 0.9),
        Word("say", 0.95, 1.2),
        Word("anything", 1.25, 1.9),
    ]
    doc = build_ass(words)
    times = re.findall(r"Dialogue: 0,(\d:\d\d:\d\d\.\d\d),(\d:\d\d:\d\d\.\d\d),", doc)
    assert len(times) == len(words)
    for (_, ends), (starts, _) in itertools.pairwise(times):
        assert ends <= starts  # each caption is gone before the next appears
