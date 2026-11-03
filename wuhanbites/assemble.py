from __future__ import annotations

import subprocess
from pathlib import Path


def assemble_video(images: list[Path], audio: Path, durations: list[float], config: dict, out: Path) -> Path:
    """One image per scene, shown for that scene's narration length, with a slow zoom."""
    v = config["video"]
    fps, w, h = v["fps"], v["width"], v["height"]
    cmd = ["ffmpeg", "-y"]
    for img in images:
        cmd += ["-i", str(img)]
    cmd += ["-i", str(audio)]
    n = len(images)
    parts = []
    for i, d in enumerate(durations):
        frames = max(1, round(d * fps))
        zoom = f"min(1+0.06*on/{frames},1.06)"
        parts.append(
            f"[{i}:v]scale={w * 2}:{h * 2},zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'"
            f":d={frames}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p[v{i}]"
        )
    concat = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[outv]"
    cmd += [
        "-filter_complex", ";".join(parts + [concat]),
        "-map", "[outv]", "-map", f"{n}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", "-shortest", str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out
