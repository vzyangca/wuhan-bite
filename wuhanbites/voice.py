"""Narration: one audio clip per scene, so scene length follows the spoken length.

Providers: edge-tts (free, needs internet), macos-say (offline, macOS only),
silent (placeholder), auto (try edge-tts, then macos-say, then silent).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PAD = 0.45        # seconds of silence after each scene's narration
MIN_SCENE = 2.4   # no scene shorter than this


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def _to_wav(src: Path, dst: Path) -> Path:
    """Normalize any clip to 44.1 kHz mono wav with trailing pad and a minimum length."""
    _run(["ffmpeg", "-y", "-i", str(src), "-ar", "44100", "-ac", "1",
          "-af", f"apad=pad_dur={PAD},apad=whole_dur={MIN_SCENE}", str(dst)])
    return dst


def speech_seconds(text: str) -> float:
    """Rough spoken length: ~4.2 Chinese characters/s, ~2.6 other words/s."""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    rest = "".join(" " if "\u4e00" <= ch <= "\u9fff" else ch for ch in text)
    return cjk / 4.2 + len(rest.split()) / 2.6


def silent_clip(text: str, out: Path) -> Path:
    seconds = max(MIN_SCENE, speech_seconds(text) + PAD)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{seconds:.2f}", str(out)])
    return out


def edge_tts_clip(text: str, voice_name: str, out: Path, rate: str = "+0%") -> Path:
    import asyncio

    import edge_tts  # optional dependency; needs internet

    asyncio.run(edge_tts.Communicate(text, voice_name, rate=rate).save(str(out)))
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("edge-tts produced no audio")
    return out


def say_clip(text: str, voice: str, out: Path) -> Path:
    cmd = ["say", "-o", str(out)]
    if voice:
        cmd += ["-v", voice]
    _run(cmd + [text])
    return out


def _synth(provider: str, text: str, config: dict, raw: Path) -> Path:
    v = config["voice"]
    zh = config.get("language") == "zh"
    if provider == "edge-tts":
        return edge_tts_clip(text, v["voice_name_zh"] if zh else v["voice_name"], raw.with_suffix(".mp3"),
                             v.get("rate", "+0%"))
    if provider == "macos-say":
        return say_clip(text, v.get("say_voice_zh", "Tingting") if zh else v.get("say_voice", ""), raw.with_suffix(".aiff"))
    return silent_clip(text, raw.with_suffix(".wav"))


def generate_voice(script: dict, config: dict, out_base: Path) -> tuple[Path, list[float]]:
    """Return (combined wav, per-scene durations in seconds)."""
    parts = out_base.parent / "voice_parts"
    parts.mkdir(parents=True, exist_ok=True)
    wanted = config["voice"]["provider"]
    chain = ["edge-tts", "macos-say", "silent"] if wanted == "auto" else [wanted, "silent"]
    if "macos-say" in chain and not shutil.which("say"):
        chain.remove("macos-say")

    used, wavs = None, []
    for provider in chain:
        try:
            wavs = []
            for i, scene in enumerate(script["scenes"]):
                spoken = scene.get("tts") or scene["narration"]  # `tts_zh` in the topic can respell a hard word
                raw = _synth(provider, spoken, config, parts / f"scene_{i:02d}_raw")
                wavs.append(_to_wav(raw, parts / f"scene_{i:02d}.wav"))
            used = provider
            break
        except Exception as e:  # noqa: BLE001 - fall back to the next provider
            print(f"voice: {provider} failed ({type(e).__name__}: {str(e)[:80]}); trying next")
    if used is None:
        raise RuntimeError("no voice provider worked")
    print(f"voice: using {used}")

    durations = [duration(w) for w in wavs]
    listing = parts / "list.txt"
    listing.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    out = out_base.with_suffix(".wav")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(out)])
    return out, durations


MANDARIN_VOICES = ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunxiNeural", "zh-CN-YunyangNeural", "zh-CN-YunjianNeural"]


def _main() -> None:
    """python3 -m wuhanbites.voice list | audition"""
    import argparse
    import asyncio

    import edge_tts

    from .common import ROOT, load_topics

    ap = argparse.ArgumentParser(prog="wuhanbites.voice")
    ap.add_argument("cmd", choices=["list", "audition"], help="list: Mandarin voices; audition: sample each one")
    cmd = ap.parse_args().cmd
    if cmd == "list":
        voices = asyncio.run(edge_tts.list_voices())
        for v in voices:
            if v["Locale"].startswith("zh-"):
                print(f"{v['ShortName']:28} {v['Gender']:7} {v['Locale']}")
        return
    topic = load_topics()["re-gan-mian"]
    text = "".join(s["narration_zh"] for s in topic["scenes"][:2])
    out = ROOT / "output" / "voice_samples"
    out.mkdir(parents=True, exist_ok=True)
    for name in MANDARIN_VOICES:
        path = out / f"{name}.mp3"
        try:
            edge_tts_clip(text, name, path)
            print(f"ok      {path}")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED  {name}: {str(e)[:100]}")
    print(f"Listen with: open {out}")


if __name__ == "__main__":
    _main()
