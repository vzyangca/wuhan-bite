from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PALETTE = [(176, 48, 36), (222, 140, 40), (60, 110, 80), (40, 70, 110)]


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def placeholder_image(caption: str, idx: int, size: tuple[int, int], out: Path) -> Path:
    img = Image.new("RGB", size, PALETTE[idx % len(PALETTE)])
    draw = ImageDraw.Draw(img)
    font = _font(size[0] // 14)
    text = "\n".join(textwrap.wrap(caption, width=18))
    draw.multiline_text(
        (size[0] // 2, size[1] // 2), text, font=font, fill="white", anchor="mm", align="center"
    )
    img.save(out)
    return out


def generate_image(scene: dict, idx: int, config: dict, out: Path) -> Path:
    """Replace the placeholder branch with a real image-generation provider.

    Keep the contract: write an image file to `out` and return its path.
    """
    size = (config["video"]["width"], config["video"]["height"])
    return placeholder_image(scene["caption"], idx, size, out)


def generate_images(script: dict, config: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        generate_image(s, i, config, out_dir / f"scene_{i:02d}.png")
        for i, s in enumerate(script["scenes"])
    ]
