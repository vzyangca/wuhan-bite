"""Scene images.

`illustrated` (default): original flat illustrations drawn locally with Pillow
(no network, no licensing issues), with headline + subtitle text.
`placeholder`: plain colored title cards.
To use a real image-generation API, add a branch in `generate_image()`.
"""
from __future__ import annotations

import math
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LW, LH = 1080, 1920  # logical canvas; everything is drawn in these units
VISUALS = ("skyline", "lanterns", "bowl", "pocket", "ring", "pot", "lotus", "wok", "follow")
GRADIENTS = [
    ((255, 205, 130), (206, 62, 44)),
    ((255, 228, 160), (226, 112, 48)),
    ((250, 190, 120), (150, 40, 50)),
    ((255, 214, 140), (196, 80, 40)),
]
PLACEHOLDER_PALETTE = [(176, 48, 36), (222, 140, 40), (60, 110, 80), (40, 70, 110)]
FONT_CANDIDATES = [
    "Poppins-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]


def _font(size: int):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize and center-crop to exactly `size` (no stretching)."""
    w, h = size
    scale = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


class Canvas:
    """Draws in logical 1080x1920 units, supersampled for smooth edges."""

    def __init__(self, size: tuple[int, int], gradient, ss: int = 2, photo: Image.Image | None = None):
        self.size, self.ss = size, ss
        self.k = size[0] / LW * ss
        w, h = round(size[0] * ss), round(size[1] * ss)
        top, bottom = gradient
        if photo is not None:
            self.img = _cover(photo.convert("RGB"), (w, h))
        else:
            grad = Image.linear_gradient("L").resize((w, h))
            self.img = Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), grad)
        self.d = ImageDraw.Draw(self.img, "RGBA")
        self.bottom = bottom

    def _b(self, b):
        return [v * self.k for v in b]

    def _pts(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def ell(self, b, fill, outline=None, w=0):
        self.d.ellipse(self._b(b), fill=fill, outline=outline, width=max(1, round(w * self.k)) if outline else 0)

    def pie(self, b, a0, a1, fill):
        self.d.pieslice(self._b(b), a0, a1, fill=fill)

    def rect(self, b, fill, r=0):
        if r:
            self.d.rounded_rectangle(self._b(b), radius=r * self.k, fill=fill)
        else:
            self.d.rectangle(self._b(b), fill=fill)

    def poly(self, pts, fill):
        self.d.polygon(self._pts(pts), fill=fill)

    def line(self, pts, fill, w):
        self.d.line(self._pts(pts), fill=fill, width=max(1, round(w * self.k)), joint="curve")

    def text(self, xy, s, size, fill="white", anchor="mm", shadow=True, align="center", spacing=8):
        f = _font(round(size * self.k))
        x, y = xy[0] * self.k, xy[1] * self.k
        if shadow:
            self.d.multiline_text((x + 4 * self.k, y + 5 * self.k), s, font=f, fill=(0, 0, 0, 120),
                                  anchor=anchor, align=align, spacing=spacing * self.k)
        self.d.multiline_text((x, y), s, font=f, fill=fill, anchor=anchor, align=align, spacing=spacing * self.k)

    def wrap(self, s: str, size: int, max_w: int) -> str:
        f = _font(round(size * self.k))
        lines, cur = [], ""
        for word in s.split():
            test = (cur + " " + word).strip()
            if f.getlength(test) <= max_w * self.k or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        return "\n".join(lines + [cur])

    def finish(self) -> Image.Image:
        return self.img.resize(self.size, Image.LANCZOS)


def _steam(c: Canvas, cx, y0, n=3, h=250, spread=120):
    for i in range(n):
        x = cx + (i - (n - 1) / 2) * spread
        pts = [(x + 28 * math.sin(t / 25 + i), y0 - t) for t in range(0, h, 10)]
        c.line(pts, (255, 255, 255, 110), 16)


def _flecks(c: Canvas, rng, n, inside, colors, size=(10, 18)):
    for _ in range(n):
        for _try in range(30):
            x, y = rng.uniform(0, LW), rng.uniform(300, 1500)
            if inside(x, y):
                s = rng.uniform(*size)
                c.ell((x - s, y - s * 0.6, x + s, y + s * 0.6), rng.choice(colors))
                break


# ---- visuals -------------------------------------------------------------------------
def art_bowl(c, cx=540, cy=980):
    rng = random.Random(1)
    c.ell((cx - 380, cy + 240, cx + 380, cy + 330), (0, 0, 0, 60))
    c.pie((cx - 340, cy - 250, cx + 340, cy + 250), 0, 180, (176, 48, 36))
    c.rect((cx - 130, cy + 235, cx + 130, cy + 275), (120, 30, 24), r=12)
    c.line([(cx - 300, cy + 90), (cx, cy + 150), (cx + 300, cy + 90)], (250, 220, 170, 200), 10)
    c.ell((cx - 340, cy - 50, cx + 340, cy + 50), (250, 238, 214))
    c.ell((cx - 310, cy - 40, cx + 310, cy + 34), (215, 160, 60))
    dome = (cx - 260, cy - 210, cx + 260, cy + 70)
    c.pie(dome, 180, 360, (240, 196, 92))
    inside = lambda x, y: ((x - cx) / 255) ** 2 + ((y - (cy - 70)) / 135) ** 2 < 1 and y < cy - 62
    for r in range(12):  # noodle strands
        base = cy - 190 + r * 11
        seg = []
        for x in range(cx - 250, cx + 251, 8):
            y = base + 7 * math.sin(x / 22 + r)
            if inside(x, y):
                seg.append((x, y))
            elif len(seg) > 1:
                c.line(seg, (196, 142, 46, 190), 4)
                seg = []
            else:
                seg = []
        if len(seg) > 1:
            c.line(seg, (196, 142, 46, 190), 4)
    for i in range(3):  # sesame sauce drizzle
        pts = [(cx - 190 + t, cy - 150 + i * 28 + 10 * math.sin(t / 30 + i)) for t in range(0, 380, 12)]
        c.line([p for p in pts if inside(*p)] or pts[:2], (112, 66, 36, 235), 14)
    _flecks(c, rng, 28, inside, [(70, 150, 70), (96, 176, 84)], (7, 12))        # scallion
    _flecks(c, rng, 14, inside, [(214, 64, 40), (230, 110, 40)], (6, 10))       # chili / pickles
    _steam(c, cx, cy - 235)


def art_pocket(c, cx=540, cy=980):
    rng = random.Random(2)
    c.ell((cx - 400, cy + 180, cx + 400, cy + 300), (255, 244, 224, 235))
    c.rect((cx - 330, cy - 110, cx + 330, cy + 190), (0, 0, 0, 50), r=34)
    c.rect((cx - 330, cy - 130, cx + 330, cy + 170), (218, 156, 52), r=34)      # bottom skin
    c.rect((cx - 312, cy - 70, cx + 312, cy + 110), (250, 240, 216), r=18)      # sticky rice
    inside = lambda x, y: cx - 300 < x < cx + 300 and cy - 62 < y < cy + 102
    _flecks(c, rng, 22, inside, [(120, 74, 44), (214, 120, 110)], (11, 20))     # mushroom / pork
    _flecks(c, rng, 12, inside, [(236, 214, 150)], (9, 14))                     # dried tofu
    c.rect((cx - 330, cy - 250, cx + 330, cy - 90), (232, 170, 62), r=34)       # crisp top skin
    for x in range(cx - 270, cx + 300, 90):
        c.line([(x, cy - 232), (x, cy - 108)], (190, 124, 36, 150), 8)
    c.line([(cx - 300, cy - 190), (cx + 300, cy - 190)], (190, 124, 36, 150), 8)
    _steam(c, cx, cy - 270, h=210)


def art_ring(c, cx=540, cy=1000):
    rng = random.Random(3)
    c.ell((cx - 420, cy + 150, cx + 420, cy + 290), (255, 244, 224, 235))
    for dx, dy, s in ((-210, -40, 0.62), (200, -10, 0.58)):
        x, y = cx + dx, cy + dy
        c.ell((x - 300 * s, y - 190 * s, x + 300 * s, y + 190 * s), (190, 116, 40))
        c.ell((x - 110 * s, y - 70 * s, x + 110 * s, y + 70 * s), (255, 244, 224, 235))
    ox, oy = cx, cy + 20
    c.ell((ox - 310, oy - 165, ox + 310, oy + 215), (0, 0, 0, 55))
    c.ell((ox - 300, oy - 190, ox + 300, oy + 190), (214, 140, 48))
    c.ell((ox - 250, oy - 160, ox + 250, oy + 150), (232, 166, 62))
    c.ell((ox - 115, oy - 75, ox + 115, oy + 75), (255, 244, 224))
    c.ell((ox - 105, oy - 66, ox + 105, oy + 66), (0, 0, 0, 40))
    inside = lambda x, y: ((x - ox) / 290) ** 2 + ((y - oy) / 180) ** 2 < 1 and ((x - ox) / 125) ** 2 + ((y - oy) / 85) ** 2 > 1
    _flecks(c, rng, 40, inside, [(255, 244, 214), (100, 140, 60)], (5, 9))
    _steam(c, cx, cy - 210, h=190)


def art_wok(c, cx=540, cy=960):
    rng = random.Random(4)
    for i, (dx, h) in enumerate(((-230, 150), (-110, 210), (0, 250), (120, 200), (240, 140))):
        x = cx + dx
        c.poly([(x - 55, cy + 330), (x, cy + 330 - h - 60), (x + 55, cy + 330)], (255, 150, 40, 230))
        c.poly([(x - 28, cy + 330), (x, cy + 330 - h * 0.65), (x + 28, cy + 330)], (255, 224, 90, 240))
    c.pie((cx - 380, cy - 200, cx + 380, cy + 300), 0, 180, (48, 44, 44))
    c.line([(cx - 330, cy + 20), (cx - 520, cy - 40)], (48, 44, 44), 34)
    c.line([(cx + 330, cy + 20), (cx + 520, cy - 40)], (48, 44, 44), 34)
    c.ell((cx - 380, cy - 50, cx + 380, cy + 50), (86, 80, 80))
    c.ell((cx - 350, cy - 40, cx + 350, cy + 38), (236, 168, 62))
    c.ell((cx - 220, cy - 30, cx - 60, cy), (255, 220, 140, 150))
    inside = lambda x, y: ((x - cx) / 340) ** 2 + ((y - cy) / 36) ** 2 < 1
    _flecks(c, rng, 18, inside, [(250, 236, 190), (110, 160, 70), (200, 70, 40)], (8, 16))
    for i in range(8):  # splashing droplets
        a = rng.uniform(0, math.pi)
        r = rng.uniform(70, 170)
        c.ell((cx + 250 * math.cos(a) - 8, cy - 40 - r * math.sin(a) - 8, cx + 250 * math.cos(a) + 8, cy - 40 - r * math.sin(a) + 8), (255, 214, 120, 220))
    _steam(c, cx, cy - 80, h=240, spread=170)


def _lotus_slice(c, x, y, r, tint=(244, 228, 200)):
    c.ell((x - r - 6, y - r - 6, x + r + 6, y + r + 6), (150, 110, 80, 220))
    c.ell((x - r, y - r, x + r, y + r), tint)
    for i in range(7):
        a = i * math.tau / 6
        hx, hy = (x, y) if i == 6 else (x + 0.5 * r * math.cos(a), y + 0.5 * r * math.sin(a))
        hr = r * (0.2 if i == 6 else 0.17)
        c.ell((hx - hr, hy - hr, hx + hr, hy + hr), (176, 132, 96))


def art_pot(c, cx=540, cy=980):
    rng = random.Random(5)
    c.ell((cx - 400, cy + 240, cx + 400, cy + 330), (0, 0, 0, 60))
    c.line([(cx - 330, cy - 10), (cx - 440, cy - 50), (cx - 430, cy + 40)], (96, 52, 38), 34)
    c.line([(cx + 330, cy - 10), (cx + 440, cy - 50), (cx + 430, cy + 40)], (96, 52, 38), 34)
    c.pie((cx - 350, cy - 260, cx + 350, cy + 270), 0, 180, (134, 72, 48))
    c.ell((cx - 350, cy - 70, cx + 350, cy + 70), (108, 58, 40))
    c.ell((cx - 318, cy - 56, cx + 318, cy + 56), (232, 196, 120))
    for x, y in ((-170, -6), (10, 16), (180, -10)):
        _lotus_slice(c, cx + x, cy + y, 52)
    for x, y in ((-80, -20), (100, -14), (-230, 12)):
        c.rect((cx + x - 40, cy + y - 12, cx + x + 40, cy + y + 12), (150, 84, 56), r=10)
        c.rect((cx + x - 18, cy + y - 6, cx + x + 18, cy + y + 6), (244, 226, 200), r=4)
    for i in range(6):
        x, y = cx + rng.uniform(-260, 260), cy + rng.uniform(-30, 30)
        c.ell((x - 8, y - 5, x + 8, y + 5), (110, 160, 70, 220))
    _steam(c, cx, cy - 90, h=260, spread=140)


def art_lotus(c, cx=540, cy=980):
    c.ell((cx - 430, cy - 150, cx + 430, cy + 300), (70, 140, 90, 235))
    c.ell((cx - 360, cy - 110, cx + 360, cy + 250), (92, 168, 108, 240))
    for a in range(0, 360, 40):
        c.line([(cx, cy + 70), (cx + 340 * math.cos(math.radians(a)), cy + 70 + 160 * math.sin(math.radians(a)))], (60, 120, 80, 150), 5)
    for x, y, r in ((-170, 20, 150), (150, 40, 150), (-10, 160, 120)):
        _lotus_slice(c, cx + x, cy + y, r)
    for k, (dx, ang) in enumerate(((-90, -25), (0, 0), (90, 25))):  # simple pink lotus flower
        a = math.radians(ang - 90)
        tip = (cx + dx + 150 * math.cos(a) * 0.6, cy - 190 + 150 * math.sin(a) * 0.4)
        c.poly([(cx + dx - 52, cy - 70), tip, (cx + dx + 52, cy - 70)], (244, 150, 170, 240))
    c.poly([(cx - 52, cy - 70), (cx, cy - 330), (cx + 52, cy - 70)], (250, 176, 192, 245))


def art_skyline(c, cx=540, cy=980):
    c.ell((cx - 220, cy - 380, cx + 220, cy + 60), (255, 244, 200, 190))
    c.poly([(0, cy + 90), (160, cy - 30), (330, cy + 50), (520, cy - 60), (760, cy + 40), (940, cy - 20), (LW, cy + 70), (LW, cy + 140), (0, cy + 140)], (150, 70, 62, 150))
    base = cy + 150
    c.rect((cx - 230, base - 40, cx + 230, base + 20), (110, 52, 44))
    y = base - 40
    for i in range(5):
        w = 330 - i * 52
        c.rect((cx - w / 2, y - 62, cx + w / 2, y), (166, 48, 36))
        c.poly([(cx - w / 2 - 56, y - 62), (cx - w / 2 - 6, y - 98), (cx + w / 2 + 6, y - 98), (cx + w / 2 + 56, y - 62), (cx + w / 2 + 6, y - 74), (cx - w / 2 - 6, y - 74)], (70, 44, 38))
        y -= 90
    c.poly([(cx - 8, y + 10), (cx, y - 70), (cx + 8, y + 10)], (70, 44, 38))
    for i, col in enumerate(((60, 120, 170), (46, 98, 150), (34, 78, 128))):
        top = cy + 200 + i * 55
        pts = [(x, top + 10 * math.sin(x / 55 + i * 2)) for x in range(-20, LW + 40, 20)]
        c.poly(pts + [(LW + 40, top + 200), (-20, top + 200)], col + (235,))
    for bx, by in ((250, cy - 250), (310, cy - 215), (800, cy - 280)):
        c.line([(bx - 22, by), (bx, by - 10), (bx + 22, by)], (90, 40, 40), 5)


def art_lanterns(c, cx=540, cy=980):
    c.line([(40, cy - 330), (cx, cy - 250), (LW - 40, cy - 330)], (90, 40, 30), 7)
    for x, drop, s in ((130, 100, 0.9), (320, 190, 1.1), (540, 140, 1.25), (760, 190, 1.1), (950, 100, 0.9)):
        top = cy - 300 + drop * 0.6 + (abs(x - cx) / 410) * -60 + 60
        c.line([(x, top - 40), (x, top)], (90, 40, 30), 6)
        c.ell((x - 110 * s, top - 40 * s, x + 110 * s, top + 280 * s), (255, 190, 70, 70))
        c.ell((x - 80 * s, top, x + 80 * s, top + 190 * s), (206, 36, 34))
        for dx in (-50, -22, 0, 22, 50):
            c.line([(x + dx * s * 0.9, top + 14 * s), (x + dx * s * 0.8, top + 176 * s)], (240, 100, 60, 150), 3)
        c.rect((x - 40 * s, top - 14 * s, x + 40 * s, top + 8 * s), (236, 190, 70), r=4)
        c.rect((x - 40 * s, top + 182 * s, x + 40 * s, top + 204 * s), (236, 190, 70), r=4)
        c.line([(x, top + 204 * s), (x, top + 270 * s)], (236, 190, 70), 6)
    c.ell((cx - 360, cy + 220, cx + 360, cy + 320), (0, 0, 0, 40))
    c.text((cx, cy + 210), "street food stalls", 54, fill=(255, 244, 220), shadow=True)


def art_follow(c, cx=540, cy=980):
    c.ell((cx - 250, cy - 330, cx + 250, cy + 170), (255, 244, 224, 235))
    r = 105
    c.ell((cx - 2 * r + 20, cy - 190, cx + 20, cy - 190 + 2 * r), (214, 40, 52))
    c.ell((cx - 20, cy - 190, cx + 2 * r - 20, cy - 190 + 2 * r), (214, 40, 52))
    c.poly([(cx - 2 * r + 25, cy - 105), (cx + 2 * r - 25, cy - 105), (cx, cy + 90)], (214, 40, 52))
    c.rect((cx - 250, cy + 260, cx + 250, cy + 390), (214, 40, 52), r=64)
    c.text((cx, cy + 325), "+  Follow", 78, fill="white", shadow=False)


ART = {
    "skyline": art_skyline, "lanterns": art_lanterns, "bowl": art_bowl, "pocket": art_pocket,
    "ring": art_ring, "pot": art_pot, "lotus": art_lotus, "wok": art_wok, "follow": art_follow,
}


# ---- composition ---------------------------------------------------------------------
def _overlay(c: Canvas, scene: dict, channel: str, scrim: bool = False) -> None:
    """Channel badge, headline and subtitle, shared by illustrated and photo scenes."""
    if scrim:  # smooth dark gradients at top and bottom keep text readable on busy photos
        w = c.img.width
        for y0, y1, flip, peak in ((0, 520, True, 0.62), (1220, LH, False, 0.62)):
            hh = round((y1 - y0) * c.k)
            mask = Image.linear_gradient("L").resize((w, hh))
            if flip:
                mask = mask.transpose(Image.FLIP_TOP_BOTTOM)
            mask = mask.point(lambda v: int(255 * peak * (v / 255) ** 1.4))
            c.img.paste(Image.new("RGB", (w, hh), (0, 0, 0)), (0, round(y0 * c.k)), mask)
    c.rect((60, 70, 60 + 24 * len(channel) + 90, 150), (0, 0, 0, 90), r=40)
    c.text((60 + (24 * len(channel) + 90) / 2, 110), channel, 40, fill=(255, 240, 210), shadow=False)
    size = 100
    head = c.wrap(scene["caption"], size, 920)
    while head.count("\n") >= 2 and size > 60:  # keep headlines to two lines
        size -= 6
        head = c.wrap(scene["caption"], size, 920)
    c.text((LW / 2, 290), head, size)
    sub = c.wrap(scene["narration"], 54, 860)
    h = (sub.count("\n") + 1) * 74 + 70
    top = 1390
    c.rect((90, top, LW - 90, top + h), (0, 0, 0, 130), r=40)
    c.text((LW / 2, top + h / 2), sub, 54, shadow=False, spacing=12)


def illustrated_image(scene: dict, idx: int, size: tuple[int, int], out: Path, channel: str = "Wuhan Bites") -> Path:
    c = Canvas(size, GRADIENTS[idx % len(GRADIENTS)])
    for x, y, r in ((120, 380, 180), (960, 1500, 260), (900, 260, 110)):  # soft background shapes
        c.ell((x - r, y - r, x + r, y + r), (255, 255, 255, 22))
    ART.get(scene.get("visual"), art_lanterns)(c)
    _overlay(c, scene, channel)
    c.finish().save(out)
    return out


def photo_image(scene: dict, photo: Image.Image, size: tuple[int, int], out: Path, channel: str = "Wuhan Bites") -> Path:
    c = Canvas(size, GRADIENTS[0], photo=photo)
    _overlay(c, scene, channel, scrim=True)
    c.finish().save(out)
    return out


def placeholder_image(caption: str, idx: int, size: tuple[int, int], out: Path) -> Path:
    img = Image.new("RGB", size, PLACEHOLDER_PALETTE[idx % len(PLACEHOLDER_PALETTE)])
    draw = ImageDraw.Draw(img)
    font = _font(size[0] // 14)
    text = "\n".join(textwrap.wrap(caption, width=18))
    draw.multiline_text((size[0] // 2, size[1] // 2), text, font=font, fill="white", anchor="mm", align="center")
    img.save(out)
    return out


def _cached_photo(prompt: str, config: dict) -> Image.Image:
    """Generate (or reuse) a photo for this prompt. Cached so repeat runs cost nothing."""
    import hashlib

    from .common import ROOT
    from .image_providers import DEFAULT_MODELS, STYLE, generate

    model = config["images"].get("google_model") or DEFAULT_MODELS["google"]
    key = hashlib.sha1(f"{model}|{STYLE}|{prompt}".encode()).hexdigest()[:16]
    path = ROOT / "cache" / "images" / f"{key}.png"
    if path.exists():
        return Image.open(path).convert("RGB")
    img = generate("google", prompt, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img


def _wants_photos(config: dict) -> bool:
    from .image_providers import api_key

    provider = config["images"]["provider"]
    if provider == "google":
        return True
    return provider == "auto" and bool(api_key("google"))


def generate_image(scene: dict, idx: int, config: dict, out: Path) -> Path:
    """Photos from Google when asked for (or `auto` with a key); otherwise, or on any failure,
    the local illustrated scene. Add other providers here: write a file to `out`, return it."""
    size = (config["video"]["width"], config["video"]["height"])
    channel = config["channel_name"]
    provider = config["images"]["provider"]
    if provider == "placeholder":
        return placeholder_image(scene["caption"], idx, size, out)
    if scene.get("image_prompt") and _wants_photos(config):
        try:
            return photo_image(scene, _cached_photo(scene["image_prompt"], config), size, out, channel)
        except Exception as e:  # noqa: BLE001 - never lose a video over one image
            print(f"images: scene {idx} photo failed ({str(e)[:120]}); using illustration")
    return illustrated_image(scene, idx, size, out, channel)


def generate_images(script: dict, config: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [generate_image(s, i, config, out_dir / f"scene_{i:02d}.png") for i, s in enumerate(script["scenes"])]
