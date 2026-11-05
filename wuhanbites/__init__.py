"""Wuhan Bites: short-video pipeline."""

from pathlib import Path as _Path

try:
    __version__ = "wuhan-bite-v-" + (_Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
except OSError:
    __version__ = "wuhan-bite (unknown version)"
