from __future__ import annotations

import json
from pathlib import Path


def build_manifest(topic: dict, script: dict, video: Path, config: dict) -> dict:
    zh = config.get("language") == "zh"
    series = topic.get("series_zh") if zh else topic.get("series")
    title = (f"{topic.get('title_zh', topic['title'])} | {series or config.get('channel_name_zh', '武汉一口')}" if zh
             else f"{topic['title']} | {series or config['channel_name']}")
    description = ("" if zh else " ").join(s["narration"] for s in script["scenes"])
    sources = topic.get("sources") or []
    if sources:
        description += "\n\n" + ("资料来源：" if zh else "Sources:") + "\n" + "\n".join(f"- {x}" for x in sources)
    tags = topic.get("tags_zh" if zh else "tags")
    return {
        "language": "zh-CN" if zh else "en",
        "title": title,
        "description": description,
        "tags": tags or (["武汉", "武汉美食", "街头小吃", "中国美食", "shorts"] if zh
                         else ["wuhan", "streetfood", "chinesefood", "shorts"]),
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
    results = {}
    for platform in manifest["platforms"]:
        if platform == "youtube_shorts":
            from .youtube import upload

            results[platform] = upload(manifest, config)
            print(f"youtube_shorts: {results[platform]['url']} ({results[platform]['privacy']})")
        else:
            print(f"{platform}: no uploader implemented yet, skipped.")
    manifest["results"] = results
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return path
