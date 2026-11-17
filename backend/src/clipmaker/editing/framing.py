"""Speaker-following 9:16 framing.

1. `analyze_faces` (I/O): decode the kept stretches of the source, sample a few frames per
   second, detect faces (OpenCV YuNet, bundled model) and measure mouth movement per face.
2. `plan_shots` (pure, unit-tested): pick the active speaker over time (the face whose mouth
   moves most, smoothed so the frame doesn't jitter), split into shots when the speaker
   changes, and add punch-in zooms so something changes on screen every few seconds.
3. `crop_box`: the 9:16 crop rectangle for a shot, in source pixels.

No faces (screen recordings, B-roll) → a steady centre crop. A source that is already
vertical is never cropped.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clipmaker.editing.cuts import Interval

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "media"
    / "models"
    / ("face_detection_yunet_2023mar.onnx")
)
SAMPLE_FPS = 2.0  # twice a second is plenty to follow a speaker, and halves the decoding
DETECT_WIDTH = 640
MIN_FACE_SCORE = 0.7
TRACK_MATCH = 0.12  # max horizontal distance (fraction of width) to call it the same face
#: Below this many sightings a track's average motion is half-trusted: one lucky frame of a
#: listener mid-nod should not outrank the person who is actually speaking.
MIN_TRACK_SAMPLES = 3
MIN_SHOT_SECONDS = 1.2  # don't switch speakers faster than this
# A real editor does not cut away for a two-word interjection, and does not re-frame every
# few seconds for no reason: both read as "machine made". These are the broadcast-style
# minimums that keep the camera calm.
MIN_TURN_SECONDS = 2.0  # a speaker must hold the floor this long to earn a cut
FACE_FROM_TOP = 0.42  # face centre sits below the middle, so the eyes land near the top third
HEAD_MARGIN = 1.05  # keep this much of the face height above the eyes (hair, hats, headphones)


@dataclass(slots=True)
class Face:
    cx: float  # centre, as a fraction of frame width/height
    cy: float
    w: float  # width as a fraction of frame width
    h: float = 0.0  # height as a fraction of frame height (0 = unknown)
    motion: float = 0.0  # mouth movement (mean abs pixel change), higher = talking


@dataclass(slots=True)
class Sample:
    t: float  # source seconds
    faces: list[Face] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Shot:
    """A stretch of source video shown with one framing."""

    start: float
    end: float
    cx: float  # where to centre the crop (fraction of width)
    cy: float
    zoom: float = 1.0
    face_h: float = 0.0  # face height as a fraction of frame height (0 = unknown)


@dataclass(frozen=True, slots=True)
class Turn:
    """A stretch of source video where one diarised speaker holds the floor."""

    start: float
    end: float
    speaker: str


def turns_from_words(words: list[Any], min_seconds: float = MIN_TURN_SECONDS) -> list[Turn]:
    """Speaker turns from diarised words (pure). Short interjections join the turn before.

    The transcript already knows who is talking, sentence by sentence. Driving the camera from
    that is far steadier than guessing from mouth movement, which flickers on a laugh, a cough
    or a nod — the twitchy cutting that makes automatic reframing look machine-made.
    """
    turns: list[Turn] = []
    for word in words:
        speaker = getattr(word, "speaker", None) or "?"
        if turns and turns[-1].speaker == speaker:
            turns[-1] = Turn(turns[-1].start, word.end, speaker)
        else:
            turns.append(Turn(word.start, word.end, speaker))
    merged: list[Turn] = []
    for turn in turns:
        too_short = turn.end - turn.start < min_seconds
        if merged and too_short:
            merged[-1] = Turn(merged[-1].start, turn.end, merged[-1].speaker)
        elif merged and merged[-1].speaker == turn.speaker:
            merged[-1] = Turn(merged[-1].start, turn.end, turn.speaker)
        else:
            merged.append(turn)
    return merged


def face_tracks(samples: list[Sample]) -> list[list[tuple[float, Face]]]:
    """Group face sightings into tracks by horizontal position (pure)."""
    tracks: list[list[tuple[float, Face]]] = []
    for sample in samples:
        for face in sample.faces:
            for track in tracks:
                if abs(track[-1][1].cx - face.cx) < TRACK_MATCH:
                    track.append((sample.t, face))
                    break
            else:
                tracks.append([(sample.t, face)])
    return [t for t in tracks if t]


def speaker_positions(
    samples: list[Sample], turns: list[Turn]
) -> dict[str, tuple[float, float, float]]:
    """Map each speaker to their face (cx, cy, face height), by who moves while they talk."""
    tracks = face_tracks(samples)
    if len(tracks) < 2:
        return {}
    positions: dict[str, tuple[float, float, float]] = {}
    for speaker in {t.speaker for t in turns}:
        spans = [(t.start, t.end) for t in turns if t.speaker == speaker]
        best, score = None, 0.0
        for track in tracks:
            motion = sum(f.motion for (t, f) in track if any(a <= t <= b for a, b in spans))
            if motion > score:
                best, score = track, motion
        if best is not None and score > 0:
            positions[speaker] = (
                statistics.median(f.cx for _, f in best),
                statistics.median(f.cy for _, f in best),
                statistics.median(f.h for _, f in best) if best[0][1].h else 0.0,
            )
    # Two speakers judged to be the same face means the mapping is unreliable: better to hold
    # a steady frame than to cut to the wrong person.
    if len({(round(x, 2), round(y, 2)) for x, y, _ in positions.values()}) < len(positions):
        return {}
    return positions


def _steady(samples: list[Sample], t0: float, t1: float) -> tuple[float, float, float] | None:
    """Centre of the most-talking face in [t0, t1] (fallback when diarisation can't guide us)."""
    tracks: list[list[Face]] = []
    for s in samples:
        if not t0 <= s.t <= t1:
            continue
        for f in s.faces:
            for tr in tracks:
                if abs(tr[-1].cx - f.cx) < TRACK_MATCH:
                    tr.append(f)
                    break
            else:
                tracks.append([f])
    if not tracks:
        return None

    # Mean motion, not the sum: a sum rewards whoever is on screen longest, so a listener
    # who is simply visible for more of the clip outranks the person actually talking. A
    # track still has to be seen a few times before its average is worth believing.
    def talkativeness(track: list[Face]) -> tuple[float, int]:
        seen = len(track)
        mean = sum(f.motion for f in track) / seen
        return (mean if seen >= MIN_TRACK_SAMPLES else mean * 0.5, seen)

    best = max(tracks, key=talkativeness)
    return (
        statistics.median(f.cx for f in best),
        statistics.median(f.cy for f in best),
        statistics.median(f.h for f in best) if best[0].h else 0.0,
    )


#: Where to point when a moment has no detectable face and the clip has none either. Dead
#: centre of a 16:9 frame is a guess about geometry, not about people.
BLIND_CENTRE = (0.5, 0.45, 0.0)


def fallback_place(samples: list[Sample]) -> tuple[float, float, float]:
    """Where the people are across the whole clip (pure).

    Used whenever a given moment has no face to follow. The old answer was the centre of the
    frame, which is only right if the subject happens to sit there — in an interview they do
    not, so the clip cut to a wall with the speaker sliced off the edge. The clip's own faces
    are a far better guess than the middle of a frame that was composed for 16:9.
    """
    everywhere = _steady(samples, float("-inf"), float("inf"))
    return everywhere or BLIND_CENTRE


def plan_shots(
    samples: list[Sample], intervals: list[Interval], words: list[Any] | None = None
) -> list[Shot]:
    """Framing for each kept interval: follow the speaker, punch in on long shots (pure)."""
    turns = turns_from_words(words) if words else []
    blind = fallback_place(samples)
    positions = speaker_positions(samples, turns) if turns else {}
    shots: list[Shot] = []
    for iv in intervals:
        blocks: list[list[float | str]] = []  # [start, end, cx, cy, face_h]
        if positions:
            # Follow the diarised speaker: one framing per turn, nothing shorter than a turn.
            for turn in turns:
                start, end = max(turn.start, iv.start), min(turn.end, iv.end)
                if end - start <= 0.01:
                    continue
                place = positions.get(turn.speaker)
                if place is None:
                    place = _steady(samples, start, end) or blind
                if blocks and abs(float(blocks[-1][2]) - place[0]) < TRACK_MATCH:
                    blocks[-1][1] = end
                else:
                    blocks.append([start, end, place[0], place[1], place[2]])
            if blocks:
                blocks[0][0], blocks[-1][1] = iv.start, iv.end
        if not blocks:
            # No diarisation to follow (or it was unreliable): track the moving mouth, but only
            # let the frame move after MIN_TURN_SECONDS so it never twitches.
            t = iv.start
            while t < iv.end - 1e-6:
                t1 = min(iv.end, t + MIN_TURN_SECONDS)
                if iv.end - t1 < MIN_TURN_SECONDS / 2:
                    t1 = iv.end
                place = _steady(samples, t, t1) or (
                    (float(blocks[-1][2]), float(blocks[-1][3]), float(blocks[-1][4]))
                    if blocks
                    else blind
                )
                if blocks and abs(float(blocks[-1][2]) - place[0]) < TRACK_MATCH:
                    blocks[-1][1] = t1
                else:
                    blocks.append([t, t1, place[0], place[1], place[2]])
                t = t1
        for b0, b1, cx, cy, fh in blocks:
            # One framing per speaker turn. The cut between people is the visual change; a
            # zoom every few seconds on top of it is what made clips feel machine-made.
            shots.append(Shot(float(b0), float(b1), float(cx), float(cy), 1.0, float(fh)))
    return shots


def crop_box(src_w: int, src_h: int, shot: Shot) -> tuple[int, int, int, int]:
    """(x, y, w, h) of the 9:16 crop for `shot`, clamped inside the frame. Even sizes.

    The face sits below the middle so the eyes land near the upper third — standard framing —
    and the top of the head is never cut off, whatever the zoom.
    """
    if src_w * 16 <= src_h * 9 + 1:  # already vertical (or narrower): use the whole frame
        w, h = src_w, src_h
        if shot.zoom > 1.0:
            w, h = int(src_w / shot.zoom), int(src_h / shot.zoom)
    else:
        h = int(src_h / shot.zoom)
        w = int(h * 9 / 16)
    w, h = w - w % 2, h - h % 2
    x = round(shot.cx * src_w - w / 2)
    y = round(shot.cy * src_h - h * FACE_FROM_TOP)
    if shot.face_h > 0:  # never cut the top of the head off
        head_top = (shot.cy - shot.face_h * HEAD_MARGIN) * src_h
        y = min(y, round(head_top - h * 0.03))
    x = max(0, min(src_w - w, x))
    y = max(0, min(src_h - h, y))
    return x, y, w, h


def analyze_faces(video_path: Path, intervals: list[Interval]) -> list[Sample]:
    """Sample frames in the kept intervals and measure faces + mouth movement (I/O).

    Returns an empty list if OpenCV or the model is unavailable — framing then falls back to a
    centre crop instead of failing the render.
    """
    try:
        import cv2
    except ImportError:
        return []
    if not MODEL_PATH.is_file():
        return []
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1
    scale = min(1.0, DETECT_WIDTH / src_w)
    size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    detector = cv2.FaceDetectorYN.create(str(MODEL_PATH), "", size, MIN_FACE_SCORE)
    step = max(1, round(fps / SAMPLE_FPS))
    samples: list[Sample] = []
    try:
        for iv in intervals:
            cap.set(cv2.CAP_PROP_POS_MSEC, iv.start * 1000.0)
            frame_no = 0
            prev_gray = None
            while True:
                ok = cap.grab()
                if not ok:
                    break
                t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                if t > iv.end:
                    break
                frame_no += 1
                # Decode the sampled frame and the one right before it (for mouth motion).
                if frame_no % step not in (0, step - 1 if step > 1 else 0):
                    continue
                ok, frame = cap.retrieve()
                if not ok:
                    continue
                small = cv2.resize(frame, size)
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                if frame_no % step != 0:
                    prev_gray = gray
                    continue
                _, found = detector.detect(small)
                faces: list[Face] = []
                for row in found if found is not None else []:
                    x, y, w, h = (float(v) for v in row[:4])
                    motion = 0.0
                    if prev_gray is not None:
                        # Mouth region: lower third of the face box.
                        y0, y1 = int(y + h * 0.62), int(y + h * 0.95)
                        x0, x1 = int(x + w * 0.2), int(x + w * 0.8)
                        if y1 > y0 and x1 > x0:
                            a = gray[max(0, y0) : y1, max(0, x0) : x1]
                            b = prev_gray[max(0, y0) : y1, max(0, x0) : x1]
                            if a.size and a.shape == b.shape:
                                motion = float(cv2.absdiff(a, b).mean())
                    faces.append(
                        Face(
                            cx=(x + w / 2) / size[0],
                            cy=(y + h / 2) / size[1],
                            w=w / size[0],
                            h=h / size[1],
                            motion=motion,
                        )
                    )
                samples.append(Sample(t=t, faces=faces))
                prev_gray = None
    finally:
        cap.release()
    return samples
