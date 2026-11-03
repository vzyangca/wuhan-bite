"""Text-to-image providers (REST, stdlib only). Keys come from environment variables:

  GEMINI_API_KEY (or GOOGLE_API_KEY)  -> Google Imagen via the Gemini API
  OPENAI_API_KEY                      -> OpenAI gpt-image

Every provider returns a PIL image cropped to 9:16.
"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request

from PIL import Image

STYLE = (
    "Photorealistic food photography, vertical 9:16 frame, shallow depth of field, warm natural light, "
    "authentic Wuhan, China street-food setting, appetizing, no text, no watermark, no people's faces."
)
DEFAULT_MODELS = {"google": "imagen-4.0-generate-001", "openai": "gpt-image-1"}
KEY_VARS = {"google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "openai": ("OPENAI_API_KEY",)}


def api_key(provider: str) -> str | None:
    for var in KEY_VARS[provider]:
        if os.environ.get(var):
            return os.environ[var]
    return None


def crop_9_16(img: Image.Image) -> Image.Image:
    """Center-crop to 9:16 (no stretching)."""
    w, h = img.size
    target = 9 / 16
    if w / h > target:  # too wide
        nw = round(h * target)
        left = (w - nw) // 2
        return img.crop((left, 0, left + nw, h))
    nh = round(w / target)
    top = (h - nh) // 2
    return img.crop((0, top, w, top + nh))


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {url.split('?')[0]}: {e.read().decode(errors='replace')[:300]}") from None


def _decode(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def generate_google(prompt: str, model: str, key: str) -> Image.Image:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict"
    data = _post(url, {"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}},
                 {"x-goog-api-key": key})
    return crop_9_16(_decode(data["predictions"][0]["bytesBase64Encoded"]))


def generate_openai(prompt: str, model: str, key: str, quality: str = "medium") -> Image.Image:
    data = _post("https://api.openai.com/v1/images/generations",
                 {"model": model, "prompt": prompt, "size": "1024x1536", "quality": quality, "n": 1},
                 {"Authorization": f"Bearer {key}"})
    return crop_9_16(_decode(data["data"][0]["b64_json"]))  # 2:3 -> 9:16


def generate(provider: str, prompt: str, model: str | None = None) -> Image.Image:
    key = api_key(provider)
    if not key:
        raise RuntimeError(f"No API key: set one of {', '.join(KEY_VARS[provider])}")
    model = model or DEFAULT_MODELS[provider]
    full = f"{prompt} {STYLE}"
    return generate_google(full, model, key) if provider == "google" else generate_openai(full, model, key)
