from __future__ import annotations

import json
import os


def localize(topic: dict, lang: str) -> dict:
    """Return a copy of the topic's scenes in `lang` ("en" or "zh"); each scene gets a `lang` key."""
    scenes = []
    for s in topic["scenes"]:
        s = dict(s)
        if lang == "zh":
            if not (s.get("narration_zh") and s.get("caption_zh")):
                raise SystemExit(f"Topic '{topic['slug']}' has no Mandarin text (narration_zh / caption_zh).")
            s["narration"], s["caption"] = s["narration_zh"], s["caption_zh"]
            if s.get("years_zh"):
                s["years"] = s["years_zh"]
            if s.get("tts_zh"):
                s["tts"] = s["tts_zh"]  # what the voice reads, if it needs a respelling
        s["lang"] = lang
        badge = topic.get("series_zh") if lang == "zh" else topic.get("series")
        if badge:
            s["badge"] = badge
        if topic.get("palette"):
            s.setdefault("palette", topic["palette"])
        scenes.append(s)
    return {"title": topic.get("title_zh", topic["title"]) if lang == "zh" else topic["title"], "scenes": scenes}


def template_script(topic: dict, channel: str, lang: str = "en") -> dict:
    if topic.get("scenes"):
        return localize(topic, lang)
    scenes = [{"narration": topic["hook"], "caption": topic["title"]}]
    for fact in topic["facts"]:
        scenes.append({"narration": fact, "caption": fact.split(".")[0][:60]})
    scenes.append({"narration": topic["call_to_action"], "caption": channel})
    return {"title": topic["title"], "scenes": scenes}


def anthropic_script(topic: dict, channel: str, model: str) -> dict:
    import anthropic  # optional dependency

    client = anthropic.Anthropic()
    prompt = (
        f"Write a 30-second vertical-video script for the channel '{channel}' about "
        f"{topic['title']}. Use ONLY these facts, do not invent others:\n"
        + "\n".join(f"- {f}" for f in topic["facts"])
        + f"\nStart with this hook: {topic['hook']}\nEnd with: {topic['call_to_action']}\n"
        'Return JSON only: {"title": str, "scenes": [{"narration": str, "caption": str, "visual": one of '
        "skyline|lanterns|bowl|pocket|ring|pot|lotus|wok|follow}]}"
    )
    msg = client.messages.create(
        model=model, max_tokens=800, messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(msg.content[0].text)


def generate_script(topic: dict, config: dict) -> dict:
    lang = config.get("language", "en")
    channel = config["channel_name"]
    provider = config["script"]["provider"]
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY") and lang == "en":
        return anthropic_script(topic, channel, config["script"]["model"])
    return template_script(topic, config.get("channel_name_zh", channel) if lang == "zh" else channel, lang)
