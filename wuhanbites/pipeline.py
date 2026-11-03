from __future__ import annotations

import argparse
import json

from .assemble import assemble_video
from .common import ROOT, load_config, load_topics
from .images import generate_images
from .publish import build_manifest, publish
from .script_gen import generate_script
from .voice import generate_voice


def run(slug: str) -> None:
    config = load_config()
    topics = load_topics()
    if slug not in topics:
        raise SystemExit(f"Unknown topic '{slug}'. Try: {', '.join(topics)}")
    topic = topics[slug]
    out = ROOT / "output" / slug
    out.mkdir(parents=True, exist_ok=True)

    script = generate_script(topic, config)
    (out / "script.json").write_text(json.dumps(script, indent=2, ensure_ascii=False))
    print(f"script: {len(script['scenes'])} scenes")

    images = generate_images(script, config, out / "images")
    print(f"images: {len(images)}")

    audio = generate_voice(script, config, out / "voice")
    print(f"voice: {audio.name}")

    video = assemble_video(images, audio, config, out / "video.mp4")
    print(f"video: {video}")

    publish(build_manifest(topic, script, video, config), out, config)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="wuhanbites.pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-topics")
    r = sub.add_parser("run")
    r.add_argument("--topic", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "list-topics":
        for slug, t in load_topics().items():
            print(f"{slug}\t{t['title']}")
    else:
        run(args.topic)


if __name__ == "__main__":
    main()
