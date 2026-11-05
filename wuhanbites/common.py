from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG = {
    "channel_name": "Wuhan Bites",
    "channel_name_zh": "武汉一口",
    "language": "en",
    "video": {"width": 1080, "height": 1920, "fps": 30, "seconds_per_scene": 4},
    "script": {"provider": "template", "model": "claude-sonnet-5-5"},
    "voice": {"provider": "auto", "voice_name": "en-US-AriaNeural", "say_voice": "Samantha",
              "rate": "+0%", "voice_name_zh": "zh-CN-XiaoxiaoNeural", "say_voice_zh": "Tingting"},
    "images": {"provider": "auto", "google_model": "auto"},
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


ALLOWED = {
    ("language",): {"en", "zh"},
    ("script", "provider"): {"template", "anthropic"},
    ("voice", "provider"): {"auto", "edge-tts", "macos-say", "silent"},
    ("images", "provider"): {"auto", "google", "illustrated", "placeholder"},
}


def validate_config(config: dict) -> dict:
    """Fail early with a clear message when a setting has a value that does not belong there."""
    for path, allowed in ALLOWED.items():
        value = config
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if value not in allowed:
            raise SystemExit(
                f"config.yaml: '{'.'.join(path)}' is {value!r}, but must be one of: {', '.join(sorted(allowed))}.\n"
                f"Open config.yaml and fix that line (look under the '{path[0]}:' heading)."
            )
    return config


def load_config(path: Path | None = None) -> dict:
    path = path or ROOT / "config.yaml"
    if path.exists():
        return validate_config(_merge(DEFAULT_CONFIG, yaml.safe_load(path.read_text()) or {}))
    return validate_config(dict(DEFAULT_CONFIG))


def load_topics() -> dict[str, dict]:
    topics: dict[str, dict] = {}
    for f in sorted((ROOT / "topics").glob("*.yaml")):
        data = yaml.safe_load(f.read_text()) or {}
        for t in data.get("topics", []):
            topics[t["slug"]] = t
    return topics
