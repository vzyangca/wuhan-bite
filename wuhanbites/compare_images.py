"""Generate the same scenes with each provider that has an API key and build a side-by-side sheet.

    export GEMINI_API_KEY=...   # Google AI Studio
    export OPENAI_API_KEY=...   # OpenAI
    python3 -m wuhanbites.compare_images

Costs a few cents per image (see each provider's pricing page); 3 scenes x 2 providers = 6 images.
Output: output/compare/<provider>_<scene>.png and output/compare/sheet.png
"""
from __future__ import annotations

import argparse

from PIL import Image, ImageDraw

from .common import ROOT
from .image_providers import DEFAULT_MODELS, KEY_VARS, api_key, generate
from .images import _font

SCENES = {
    "re-gan-mian": "A steaming bowl of Wuhan re gan mian hot dry noodles topped with sesame paste, scallions and pickled radish, on a street-stall table at breakfast time.",
    "doupi": "Golden pan-fried Wuhan doupi squares with sticky rice, pork and mushrooms visible in cross-section, fresh from a hot griddle at a breakfast stall.",
    "lotus-soup": "A clay pot of Wuhan lotus root and pork rib soup, thick lotus root slices with their holes visible, steam rising, rustic table.",
}


def run(providers: list[str], models: dict[str, str]) -> None:
    out = ROOT / "output" / "compare"
    out.mkdir(parents=True, exist_ok=True)
    cols: dict[str, list[Image.Image]] = {}
    for p in providers:
        if not api_key(p):
            print(f"{p}: skipped (set {' or '.join(KEY_VARS[p])})")
            continue
        cols[p] = []
        for name, prompt in SCENES.items():
            try:
                img = generate(p, prompt, models.get(p))
            except Exception as e:  # noqa: BLE001
                print(f"{p}/{name}: FAILED {e}")
                continue
            img.save(out / f"{p}_{name}.png")
            cols[p].append(img)
            print(f"{p}/{name}: ok {img.size}")
    if not cols:
        raise SystemExit("No images generated. Set at least one API key.")
    w, h, head = 360, 640, 60
    n = max(len(v) for v in cols.values())
    sheet = Image.new("RGB", (w * n, (h + head) * len(cols)), "white")
    d = ImageDraw.Draw(sheet)
    for r, (p, imgs) in enumerate(cols.items()):
        d.text((12, r * (h + head) + 16), f"{p}  ({models.get(p) or DEFAULT_MODELS[p]})", fill="black", font=_font(28))
        for c, img in enumerate(imgs):
            sheet.paste(img.resize((w, h)), (c * w, r * (h + head) + head))
    sheet.save(out / "sheet.png")
    print(f"Side-by-side sheet: {out / 'sheet.png'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--google-model", default=DEFAULT_MODELS["google"])
    ap.add_argument("--openai-model", default=DEFAULT_MODELS["openai"])
    a = ap.parse_args()
    run(["google", "openai"], {"google": a.google_model, "openai": a.openai_model})


if __name__ == "__main__":
    main()
