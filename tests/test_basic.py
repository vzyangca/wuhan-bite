from wuhanbites.common import load_config, load_topics
from wuhanbites.finance import add_entry, summarize
from wuhanbites.script_gen import template_script


def test_topics_load():
    assert "re-gan-mian" in load_topics()


def test_template_script_shape():
    topic = load_topics()["doupi"]
    script = template_script(topic, load_config()["channel_name"])
    assert script["scenes"][0]["narration"] == topic["hook"]
    assert script["scenes"][-1]["narration"] == topic["call_to_action"]


def test_finance(tmp_path):
    p = tmp_path / "ledger.csv"
    add_entry("cost", 4.5, path=p)
    add_entry("income", 12, path=p)
    assert summarize(p) == {"income": 12.0, "cost": 4.5, "net": 7.5}


def test_youtube_body_defaults_private_and_shorts_tag():
    from wuhanbites.youtube import build_body

    manifest = {"title": "Re Gan Mian | Wuhan Bites", "description": "Tasty.", "tags": ["wuhan"],
                "ai_generated_disclosure": True}
    body = build_body(manifest, load_config())
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["containsSyntheticMedia"] is True
    assert "#Shorts" in body["snippet"]["title"] and "#Shorts" in body["snippet"]["description"]
    assert len(body["snippet"]["title"]) <= 100


def test_youtube_title_truncated():
    from wuhanbites.youtube import build_body

    body = build_body({"title": "x" * 300, "description": "d"}, load_config())
    assert len(body["snippet"]["title"]) <= 100 and body["snippet"]["title"].endswith("#Shorts")


def test_youtube_rejects_bad_privacy():
    import pytest
    from wuhanbites.youtube import youtube_settings

    with pytest.raises(ValueError):
        youtube_settings({"publish": {"youtube": {"privacy": "everyone"}}})


def test_every_scene_has_known_visual_and_text():
    from wuhanbites.images import VISUALS

    for slug, topic in load_topics().items():
        assert topic["scenes"][0]["narration"] == topic["hook"], slug
        assert topic["scenes"][-1]["narration"] == topic["call_to_action"], slug
        for s in topic["scenes"]:
            assert s["visual"] in VISUALS and s["caption"] and s["narration"], (slug, s)


def test_all_visuals_render(tmp_path):
    from PIL import Image
    from wuhanbites.images import VISUALS, illustrated_image

    for i, v in enumerate(VISUALS):
        p = illustrated_image({"visual": v, "caption": "A Long Headline For Testing", "narration": "Some narration text."},
                              i, (270, 480), tmp_path / f"{v}.png")
        assert Image.open(p).size == (270, 480)


def _have_ffmpeg():
    import shutil
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def test_voice_and_video_timing_follow_narration(tmp_path, monkeypatch):
    import subprocess
    import pytest

    if not _have_ffmpeg():
        pytest.skip("ffmpeg not installed")
    from wuhanbites import voice
    from wuhanbites.assemble import assemble_video
    from wuhanbites.images import generate_images

    def fake_tts(text, voice_name, out):  # stand-in for edge-tts: longer text -> longer clip
        secs = 0.2 * len(text.split())
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=300:duration={secs}", str(out)],
                       check=True, capture_output=True)
        return out

    monkeypatch.setattr(voice, "edge_tts_clip", fake_tts)
    config = load_config()
    config["voice"]["provider"] = "edge-tts"
    config["video"].update(width=180, height=320, fps=10)
    script = {"scenes": [
        {"narration": "one two three", "caption": "A", "visual": "bowl"},
        {"narration": " ".join(["word"] * 30), "caption": "B", "visual": "wok"},
    ]}
    audio, durations = voice.generate_voice(script, config, tmp_path / "voice")
    assert durations[1] > durations[0] + 3          # long scene lasts longer
    assert durations[0] >= voice.MIN_SCENE
    images = generate_images(script, config, tmp_path / "img")
    video = assemble_video(images, audio, durations, config, tmp_path / "v.mp4")
    assert abs(voice.duration(video) - sum(durations)) < 0.5


def test_voice_falls_back_to_silent_when_provider_fails(tmp_path, monkeypatch):
    import pytest

    if not _have_ffmpeg():
        pytest.skip("ffmpeg not installed")
    from wuhanbites import voice

    def boom(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(voice, "edge_tts_clip", boom)
    config = load_config()
    config["voice"]["provider"] = "edge-tts"
    _, durations = voice.generate_voice({"scenes": [{"narration": "hello there"}]}, config, tmp_path / "voice")
    assert durations[0] >= voice.MIN_SCENE


def test_crop_9_16():
    from PIL import Image
    from wuhanbites.image_providers import crop_9_16

    for size in ((1024, 1536), (1536, 1024), (900, 1600)):
        w, h = crop_9_16(Image.new("RGB", size)).size
        assert abs(w / h - 9 / 16) < 0.01


def test_providers_parse_responses(monkeypatch):
    import base64, io
    from PIL import Image
    from wuhanbites import image_providers as ip

    buf = io.BytesIO()
    Image.new("RGB", (1024, 1536), "red").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    seen = {}

    def fake_post(url, body, headers):
        seen[url] = (body, headers)
        return {"predictions": [{"bytesBase64Encoded": b64}]} if "googleapis" in url else {"data": [{"b64_json": b64}]}

    monkeypatch.setattr(ip, "_post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    for provider in ("google", "openai"):
        w, h = ip.generate(provider, "a bowl").size
        assert abs(w / h - 9 / 16) < 0.01
    google_body = next(b for u, (b, _) in seen.items() if "googleapis" in u)
    assert google_body["parameters"]["aspectRatio"] == "9:16"


def test_missing_key_message(monkeypatch):
    import pytest
    from wuhanbites import image_providers as ip

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        ip.generate("google", "x")
