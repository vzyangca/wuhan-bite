from __future__ import annotations

import subprocess
from pathlib import Path


def silent_track(seconds: float, out: Path) -> Path:
    out = out.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(seconds), str(out)],
        check=True, capture_output=True,
    )
    return out


def edge_tts_track(text: str, voice_name: str, out: Path) -> Path:
    import asyncio

    import edge_tts  # optional dependency

    out = out.with_suffix(".mp3")
    asyncio.run(edge_tts.Communicate(text, voice_name).save(str(out)))
    return out


def generate_voice(script: dict, config: dict, out_base: Path) -> Path:
    provider = config["voice"]["provider"]
    if provider == "edge-tts":
        text = " ".join(s["narration"] for s in script["scenes"])
        return edge_tts_track(text, config["voice"]["voice_name"], out_base)
    seconds = len(script["scenes"]) * config["video"]["seconds_per_scene"]
    return silent_track(seconds, out_base)
