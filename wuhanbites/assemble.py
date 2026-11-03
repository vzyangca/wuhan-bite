from __future__ import annotations

import subprocess
from pathlib import Path


def assemble_video(images: list[Path], audio: Path, config: dict, out: Path) -> Path:
    v = config["video"]
    per = v["seconds_per_scene"]
    cmd = ["ffmpeg", "-y"]
    for img in images:
        cmd += ["-loop", "1", "-t", str(per), "-i", str(img)]
    cmd += ["-i", str(audio)]
    n = len(images)
    scale = f"scale={v['width']}:{v['height']},setsar=1,fps={v['fps']},format=yuv420p"
    parts = "".join(f"[{i}:v]{scale}[v{i}];" for i in range(n))
    concat = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[outv]"
    cmd += [
        "-filter_complex", parts + concat,
        "-map", "[outv]", "-map", f"{n}:a",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out
