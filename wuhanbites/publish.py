from __future__ import annotations

import json
from pathlib import Path


def build_manifest(topic: dict, script: dict, video: Path, config: dict) -> dict:
    title = f"{topic['title']} | {config['channel_name']}"
    return {
        "title": title,
        "description": " ".join(s["narration"] for s in script["scenes"]),
        "tags": ["wuhan", "streetfood", "chinesefood", "shorts"],
        "video": str(video),
        "ai_generated_disclosure": True,
        "platforms": config["publish"]["platforms"],
    }


def publish(manifest: dict, out_dir: Path, config: dict) -> Path:
    path = out_dir / "publish.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    if config["publish"]["dry_run"]:
        print(f"[dry-run] manifest written to {path}; nothing uploaded.")
        return path
    raise NotImplementedError(
        "Add a platform uploader (YouTube Data API, TikTok Content Posting API, ...) here."
    )
