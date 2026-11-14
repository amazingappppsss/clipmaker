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

from clipmaker.editing.cuts import Interval

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "media"
    / "models"
    / ("face_detection_yunet_2023mar.onnx")
)
SAMPLE_FPS = 4.0
DETECT_WIDTH = 640
MIN_FACE_SCORE = 0.7
TRACK_MATCH = 0.12  # max horizontal distance (fraction of width) to call it the same face
MIN_SHOT_SECONDS = 1.2  # don't switch speakers faster than this
PUNCH_IN_EVERY = 6.0  # split long shots so the picture changes at least this often
PUNCH_IN_ZOOM = 1.15


@dataclass(slots=True)
class Face:
    cx: float  # centre, as a fraction of frame width/height
    cy: float
    w: float  # width as a fraction of frame width
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


def _active_x(samples: list[Sample], t0: float, t1: float) -> tuple[float, float] | None:
    """Centre of the most-talking face in [t0, t1] (by summed mouth motion per face track)."""
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
    best = max(tracks, key=lambda tr: (sum(f.motion for f in tr), len(tr)))
    return statistics.median(f.cx for f in best), statistics.median(f.cy for f in best)


def plan_shots(samples: list[Sample], intervals: list[Interval]) -> list[Shot]:
    """Framing for each kept interval: follow the speaker, punch in on long shots (pure)."""
    shots: list[Shot] = []
    for iv in intervals:
        # 1) Split the interval into windows and find who is talking in each.
        windows: list[tuple[float, float, tuple[float, float] | None]] = []
        t = iv.start
        while t < iv.end - 1e-6:
            t1 = min(iv.end, t + MIN_SHOT_SECONDS)
            if iv.end - t1 < MIN_SHOT_SECONDS / 2:  # don't leave a sliver at the end
                t1 = iv.end
            windows.append((t, t1, _active_x(samples, t, t1)))
            t = t1
        # 2) Merge neighbouring windows that frame (almost) the same spot.
        merged: list[list[float]] = []  # [start, end, cx, cy]
        last: tuple[float, float] = (0.5, 0.5)
        for w0, w1, pos in windows:
            cx, cy = pos if pos is not None else (merged[-1][2:4] if merged else last)
            if merged and abs(merged[-1][2] - cx) < TRACK_MATCH:
                merged[-1][1] = w1
            else:
                merged.append([w0, w1, cx, cy])
            last = (cx, cy)
        # 3) Punch in/out so the picture changes at least every PUNCH_IN_EVERY seconds.
        for m0, m1, cx, cy in merged:
            pieces = max(1, int((m1 - m0) // PUNCH_IN_EVERY) + 1) if m1 - m0 > PUNCH_IN_EVERY else 1
            step = (m1 - m0) / pieces
            for k in range(pieces):
                zoom = PUNCH_IN_ZOOM if (len(shots) % 2 == 1) else 1.0
                shots.append(Shot(m0 + k * step, m0 + (k + 1) * step, cx, cy, zoom))
    return shots


def crop_box(src_w: int, src_h: int, shot: Shot) -> tuple[int, int, int, int]:
    """(x, y, w, h) of the 9:16 crop for `shot`, clamped inside the frame. Even sizes."""
    if src_w * 16 <= src_h * 9 + 1:  # already vertical (or narrower): use the whole frame
        w, h = src_w, src_h
        if shot.zoom > 1.0:
            w, h = int(src_w / shot.zoom), int(src_h / shot.zoom)
    else:
        h = int(src_h / shot.zoom)
        w = int(h * 9 / 16)
    w, h = w - w % 2, h - h % 2
    x = round(shot.cx * src_w - w / 2)
    # Keep faces in the upper part of the frame (where eyes sit in good framing).
    y = round(shot.cy * src_h - h * 0.38)
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
                            motion=motion,
                        )
                    )
                samples.append(Sample(t=t, faces=faces))
                prev_gray = None
    finally:
        cap.release()
    return samples
