from __future__ import annotations

import json
import os


def template_script(topic: dict, channel: str) -> dict:
    if topic.get("scenes"):
        return {"title": topic["title"], "scenes": [dict(s) for s in topic["scenes"]]}
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
    channel = config["channel_name"]
    provider = config["script"]["provider"]
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic_script(topic, channel, config["script"]["model"])
    return template_script(topic, channel)
