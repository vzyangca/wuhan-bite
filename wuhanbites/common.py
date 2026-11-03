from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG = {
    "channel_name": "Wuhan Bites",
    "video": {"width": 1080, "height": 1920, "fps": 30, "seconds_per_scene": 4},
    "script": {"provider": "template", "model": "claude-sonnet-5-5"},
    "voice": {"provider": "silent", "voice_name": "en-US-AriaNeural"},
    "images": {"provider": "placeholder"},
    "publish": {"dry_run": True, "platforms": ["youtube_shorts"], "youtube": {}},
}


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path | None = None) -> dict:
    path = path or ROOT / "config.yaml"
    if path.exists():
        return _merge(DEFAULT_CONFIG, yaml.safe_load(path.read_text()) or {})
    return dict(DEFAULT_CONFIG)


def load_topics() -> dict[str, dict]:
    topics: dict[str, dict] = {}
    for f in sorted((ROOT / "topics").glob("*.yaml")):
        data = yaml.safe_load(f.read_text()) or {}
        for t in data.get("topics", []):
            topics[t["slug"]] = t
    return topics
