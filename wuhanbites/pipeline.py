from __future__ import annotations

import argparse
import json

from .assemble import assemble_video
from .common import ROOT, load_config, load_topics
from .images import generate_images
from .publish import build_manifest, publish
from .script_gen import generate_script
from .voice import generate_voice


def run(slug: str, upload: bool = False, lang: str | None = None) -> None:
    config = load_config()
    if lang:
        config["language"] = lang
    zh = config["language"] == "zh"
    if upload:
        config["publish"]["dry_run"] = False
    topics = load_topics()
    if slug not in topics:
        raise SystemExit(f"Unknown topic '{slug}'. Try: {', '.join(topics)}")
    topic = topics[slug]
    out = ROOT / "output" / (f"{slug}-zh" if zh else slug)
    out.mkdir(parents=True, exist_ok=True)

    script = generate_script(topic, config)
    (out / "script.json").write_text(json.dumps(script, indent=2, ensure_ascii=False))
    print(f"script: {len(script['scenes'])} scenes")

    images = generate_images(script, config, out / "images")
    print(f"images: {len(images)}")

    audio, durations = generate_voice(script, config, out / "voice")
    print(f"voice: {audio.name} ({sum(durations):.0f}s)")

    video = assemble_video(images, audio, durations, config, out / "video.mp4")
    print(f"video: {video}")

    publish(build_manifest(topic, script, video, config), out, config)


def main(argv=None) -> None:
    from . import __version__

    ap = argparse.ArgumentParser(prog="wuhanbites.pipeline")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-topics")
    r = sub.add_parser("run")
    r.add_argument("--topic", required=True)
    r.add_argument("--lang", choices=["en", "zh"], help="narration language (default: config language)")
    r.add_argument("--upload", action="store_true", help="really upload (default is dry run)")
    sub.add_parser("auth-youtube", help="one-time YouTube login (opens a browser)")
    args = ap.parse_args(argv)
    if args.cmd == "list-topics":
        for slug, t in load_topics().items():
            print(f"{slug}\t{t['title']}")
    elif args.cmd == "auth-youtube":
        from .youtube import get_credentials

        get_credentials(load_config(), allow_login=True)
        print("YouTube login saved.")
    else:
        run(args.topic, upload=args.upload, lang=args.lang)


if __name__ == "__main__":
    main()
