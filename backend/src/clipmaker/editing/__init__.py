"""Milestone 3 editing engine: turns a picked moment into a finished vertical short.

cuts.py      smart cuts (dead air out, natural rhythm and reveal pauses kept)
framing.py   speaker-following 9:16 crop (face detection + lip motion)
captions.py  animated word-by-word captions (ASS)
render.py    FFmpeg render: teaser → rewind flash → clip, punch-ins, loudness, 1080x1920
"""
