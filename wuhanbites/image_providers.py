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
DEFAULT_MODELS = {"google": "auto", "openai": "gpt-image-1"}  # "auto": ask Google which image model your key can use
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
        body = e.read().decode(errors="replace")
        try:  # Google and OpenAI both wrap the reason in {"error": {"message": ...}}
            err = json.loads(body).get("error", {})
            msg = f"{err.get('status', '')} {err.get('message', body)}".strip()
        except (ValueError, AttributeError):
            msg = body
        raise RuntimeError(f"HTTP {e.code} {' '.join(msg.split())[:500]}") from None


def _get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {' '.join(e.read().decode(errors='replace').split())[:300]}") from None


def _decode(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


GOOGLE_API = "https://generativelanguage.googleapis.com/v1beta"
_picked: dict[str, str] = {}


def list_google_models(key: str) -> dict[str, list[str]]:
    """{model name: supported methods} for this key."""
    out: dict[str, list[str]] = {}
    token = ""
    while True:
        data = _get(f"{GOOGLE_API}/models?pageSize=200{token}", {"x-goog-api-key": key})
        for m in data.get("models", []):
            out[m["name"].removeprefix("models/")] = m.get("supportedGenerationMethods", [])
        if not data.get("nextPageToken"):
            return out
        token = f"&pageToken={data['nextPageToken']}"


def pick_google_model(key: str) -> str:
    """Prefer Imagen (predict); otherwise a Gemini image model (generateContent)."""
    if "google" in _picked:
        return _picked["google"]
    models = list_google_models(key)
    imagen = [n for n, m in models.items() if "imagen" in n and "predict" in m and "ultra" not in n]
    gemini = [n for n, m in models.items() if "image" in n and "generateContent" in m]
    gemini.sort(key=lambda n: ("flash" not in n, "preview" in n, n))  # cheaper "flash" models first
    choice = (sorted(imagen) + gemini)[0] if (imagen or gemini) else None
    if not choice:
        raise RuntimeError("This key lists no image models. Try: python3 -m wuhanbites.image_providers")
    _picked["google"] = choice
    return choice


def generate_google(prompt: str, model: str, key: str) -> Image.Image:
    headers = {"x-goog-api-key": key}
    if "imagen" in model:  # Imagen: predict
        data = _post(f"{GOOGLE_API}/models/{model}:predict",
                     {"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}}, headers)
        return crop_9_16(_decode(data["predictions"][0]["bytesBase64Encoded"]))
    data = _post(f"{GOOGLE_API}/models/{model}:generateContent",  # Gemini image models: generateContent
                 {"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}, headers)
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob:
                return crop_9_16(_decode(blob["data"]))
    reason = data.get("promptFeedback", {}).get("blockReason") or "no image in the response"
    raise RuntimeError(f"Gemini returned no image ({reason})")


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
    if provider == "google" and model == "auto":
        model = pick_google_model(key)
    full = f"{prompt} {STYLE}"
    return generate_google(full, model, key) if provider == "google" else generate_openai(full, model, key)


if __name__ == "__main__":  # python3 -m wuhanbites.image_providers : show which image models your Google key can use
    k = api_key("google")
    if not k:
        raise SystemExit("Set GEMINI_API_KEY first.")
    found = {n: m for n, m in list_google_models(k).items() if "image" in n or "imagen" in n}
    for n, m in sorted(found.items()):
        print(f"{n}  {','.join(m)}")
    print("auto would pick:", pick_google_model(k))
