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
    monkeypatch.setattr(ip, "_get", lambda url, headers: {"models": [
        {"name": "models/imagen-4.0-generate-001", "supportedGenerationMethods": ["predict"]}]})
    ip._picked.clear()
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


def test_photo_scene_has_overlay_and_correct_size(tmp_path):
    from PIL import Image
    from wuhanbites.images import photo_image

    photo = Image.new("RGB", (1024, 1536), (200, 120, 60))
    scene = {"caption": "Hot Dry Noodles", "narration": "If you only eat one breakfast in Wuhan, make it this."}
    p = photo_image(scene, photo, (270, 480), tmp_path / "p.png")
    img = Image.open(p)
    assert img.size == (270, 480)
    assert img.getpixel((135, 360)) != (200, 120, 60)  # subtitle box drawn over the photo


def test_photo_provider_caches_and_falls_back(tmp_path, monkeypatch):
    from PIL import Image
    from wuhanbites import image_providers, images

    calls = []

    def fake_generate(provider, prompt, model=None):
        calls.append(prompt)
        return Image.new("RGB", (576, 1024), "orange")

    monkeypatch.setattr(image_providers, "generate", fake_generate)
    monkeypatch.setattr("wuhanbites.common.ROOT", tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    config = load_config()
    config["video"].update(width=180, height=320)
    scene = {"caption": "A", "narration": "b", "visual": "bowl", "image_prompt": "a bowl of noodles"}
    images.generate_image(scene, 0, config, tmp_path / "a.png")
    images.generate_image(scene, 1, config, tmp_path / "b.png")
    assert len(calls) == 1  # second run served from cache

    def boom(*a, **k):
        raise RuntimeError("quota")

    monkeypatch.setattr(image_providers, "generate", boom)
    scene2 = dict(scene, image_prompt="something new")
    out = images.generate_image(scene2, 2, config, tmp_path / "c.png")  # falls back to illustration
    assert out.exists()


def test_auto_without_key_uses_illustrations(tmp_path, monkeypatch):
    from wuhanbites import images

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = load_config()
    assert images._wants_photos(config) is False


def test_mandarin_text_present_for_every_scene():
    for slug, topic in load_topics().items():
        assert topic.get("title_zh"), slug
        for s in topic["scenes"]:
            assert s.get("caption_zh") and s.get("narration_zh"), (slug, s)
            assert any("一" <= ch <= "鿿" for ch in s["narration_zh"])


def test_localize_zh_and_en():
    from wuhanbites.script_gen import template_script

    topic = load_topics()["doupi"]
    zh = template_script(topic, "武汉一口", "zh")
    assert zh["scenes"][0]["narration"] == topic["scenes"][0]["narration_zh"]
    assert all(s["lang"] == "zh" for s in zh["scenes"])
    en = template_script(topic, "Wuhan Bites", "en")
    assert en["scenes"][0]["narration"] == topic["hook"]


def test_chinese_wrap_has_no_leading_punctuation_and_fits(tmp_path):
    from PIL import Image
    from wuhanbites.images import NO_LINE_START, Canvas, illustrated_image

    c = Canvas((540, 960), ((255, 255, 255), (0, 0, 0)))
    text = "面条先煮熟，拌上油晾凉，点单的时候再放进热水里烫一下。"
    lines = c.wrap(text, 54, 860).split("\n")
    assert len(lines) >= 2 and "".join(lines) == text
    assert all(l[0] not in NO_LINE_START for l in lines)
    assert all(c.text_width(l, 54) <= 860 for l in lines)
    p = illustrated_image({"visual": "follow", "caption": "武汉一口", "narration": text, "lang": "zh"},
                          0, (270, 480), tmp_path / "zh.png", "武汉一口")
    assert Image.open(p).size == (270, 480)


def test_speech_seconds_for_chinese():
    from wuhanbites.voice import speech_seconds

    assert 3 < speech_seconds("面条先煮熟，拌上油晾凉，点单的时候再放进热水里烫一下。") < 9
    assert speech_seconds("one two three") < 2


def test_zh_manifest_and_youtube_language():
    from wuhanbites.publish import build_manifest
    from wuhanbites.script_gen import template_script
    from wuhanbites.youtube import build_body

    config = load_config()
    config["language"] = "zh"
    topic = load_topics()["re-gan-mian"]
    script = template_script(topic, "武汉一口", "zh")
    m = build_manifest(topic, script, "v.mp4", config)
    assert m["language"] == "zh-CN" and m["title"].startswith("热干面")
    body = build_body(m, config)
    assert body["snippet"]["defaultAudioLanguage"] == "zh-CN"


def test_photo_fit_modes(tmp_path):
    from PIL import Image
    from wuhanbites.images import photo_image

    wide = Image.new("RGB", (400, 300), (30, 160, 60))  # landscape photo
    scene = {"caption": "A", "narration": "b"}
    for fit in ("cover", "contain"):
        assert Image.open(photo_image(scene, wide, (270, 480), tmp_path / f"{fit}.png", fit=fit)).size == (270, 480)
    contain = Image.open(tmp_path / "contain.png").convert("RGB")
    assert contain.getpixel((135, 240))[1] > 120  # whole photo visible in the middle


def test_scene_uses_local_photo_and_falls_back_when_missing(tmp_path, monkeypatch):
    from PIL import Image
    from wuhanbites import images

    (tmp_path / "assets").mkdir()
    Image.new("RGB", (300, 340), (20, 200, 40)).save(tmp_path / "assets" / "mine.jpg")
    monkeypatch.setattr(images, "ROOT", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = load_config()
    config["video"].update(width=180, height=320)
    scene = {"caption": "A", "narration": "b", "visual": "bowl", "photo": "mine.jpg"}
    out = images.generate_image(scene, 0, config, tmp_path / "a.png")
    assert Image.open(out).convert("RGB").getpixel((90, 160))[1] > 150   # green photo in the middle
    missing = dict(scene, photo="nope.jpg")
    out2 = images.generate_image(missing, 0, config, tmp_path / "b.png")  # illustration instead of crashing
    assert out2.exists()


def test_google_http_error_is_readable_and_stops_retries(tmp_path, monkeypatch, capsys):
    import io, json, urllib.error
    from wuhanbites import image_providers, images

    body = json.dumps({"error": {"code": 400, "status": "FAILED_PRECONDITION",
                                 "message": "Imagen API is only accessible to billed users at this time."}}).encode()

    def fake_urlopen(req, timeout=0):
        raise urllib.error.HTTPError("u", 400, "Bad Request", {}, io.BytesIO(body))

    monkeypatch.setattr(image_providers.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("wuhanbites.common.ROOT", tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    config = load_config()
    config["video"].update(width=180, height=320)
    script = {"scenes": [{"caption": "A", "narration": "b", "visual": "bowl", "image_prompt": f"p{i}"} for i in range(3)]}
    outs = images.generate_images(script, config, tmp_path / "o")
    text = capsys.readouterr().out
    assert len(outs) == 3 and all(o.exists() for o in outs)  # video still builds with illustrations
    assert "FAILED_PRECONDITION" in text and "billed users" in text
    assert text.count("rejected") == 1  # reported once, not once per scene


def test_google_model_auto_pick_and_gemini_image_path(monkeypatch):
    import base64, io
    from PIL import Image
    from wuhanbites import image_providers as ip

    models = {"models": [
        {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/imagen-4.0-generate-001", "supportedGenerationMethods": ["embed"]},      # not predict-capable
        {"name": "models/gemini-2.5-flash-image", "supportedGenerationMethods": ["generateContent"]},
    ]}
    monkeypatch.setattr(ip, "_get", lambda url, headers: models)
    ip._picked.clear()
    assert ip.pick_google_model("k") == "gemini-2.5-flash-image"

    buf = io.BytesIO()
    Image.new("RGB", (1024, 1024), "blue").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    seen = {}

    def fake_post(url, body, headers):
        seen["url"], seen["body"] = url, body
        return {"candidates": [{"content": {"parts": [{"text": "ok"}, {"inlineData": {"mimeType": "image/png", "data": b64}}]}}]}

    monkeypatch.setattr(ip, "_post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    w, h = ip.generate("google", "a bowl").size
    assert abs(w / h - 9 / 16) < 0.01 and seen["url"].endswith("gemini-2.5-flash-image:generateContent")
    assert seen["body"]["generationConfig"]["responseModalities"] == ["IMAGE"]


def test_gemini_no_image_is_an_error(monkeypatch):
    import pytest
    from wuhanbites import image_providers as ip

    monkeypatch.setattr(ip, "_post", lambda *a, **k: {"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(RuntimeError, match="SAFETY"):
        ip.generate_google("p", "gemini-2.5-flash-image", "k")


def test_mandarin_default_voice_name_and_rate(monkeypatch):
    config = load_config()
    assert config["voice"]["voice_name_zh"] == "zh-CN-XiaoxiaoNeural"
    assert config["voice"]["rate"] == "+0%"


def test_tts_override_and_rate_reach_the_voice(tmp_path, monkeypatch):
    import shutil
    import subprocess
    import pytest
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    from wuhanbites import voice
    from wuhanbites.script_gen import localize

    topic = {"slug": "t", "title": "T", "scenes": [
        {"visual": "bowl", "caption": "c", "narration": "n", "caption_zh": "热干面", "narration_zh": "热干面好吃", "tts_zh": "re4 gan1 mian4 hao3 chi1"}]}
    scene = localize(topic, "zh")["scenes"][0]
    assert scene["narration"] == "热干面好吃" and scene["tts"].startswith("re4")
    seen = {}

    def fake(text, name, out, rate="+0%"):
        seen.update(text=text, name=name, rate=rate)
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=1", str(out)], check=True, capture_output=True)
        return out

    monkeypatch.setattr(voice, "edge_tts_clip", fake)
    config = load_config()
    config.update(language="zh")
    config["voice"].update(provider="edge-tts", rate="+10%")
    voice.generate_voice({"scenes": [scene]}, config, tmp_path / "voice")
    assert seen == {"text": "re4 gan1 mian4 hao3 chi1", "name": "zh-CN-XiaoxiaoNeural", "rate": "+10%"}


def test_config_validation_names_the_wrong_setting(tmp_path):
    import pytest
    from wuhanbites.common import load_config

    bad = tmp_path / "config.yaml"
    bad.write_text("voice:\n  provider: illustrated\n")  # an images value on the voice line
    with pytest.raises(SystemExit) as e:
        load_config(bad)
    msg = str(e.value)
    assert "voice.provider" in msg and "illustrated" in msg and "edge-tts" in msg
    good = tmp_path / "ok.yaml"
    good.write_text("voice:\n  provider: macos-say\nimages:\n  provider: illustrated\nlanguage: zh\n")
    assert load_config(good)["images"]["provider"] == "illustrated"


def test_version_label_matches_release_name():
    import wuhanbites

    assert wuhanbites.__version__ == "wuhan-bite-v-0.1"


def test_series_badge_and_sources_flow_to_manifest():
    from pathlib import Path
    from wuhanbites.common import load_config
    from wuhanbites.publish import build_manifest
    from wuhanbites.script_gen import localize

    topic = load_topics()["bit-story"]
    for lang in ("en", "zh"):
        script = localize(topic, lang)
        assert all(s["badge"] and s["palette"] == "blue" for s in script["scenes"])
    cfg = load_config()
    cfg["language"] = "zh"
    m = build_manifest(topic, localize(topic, "zh"), Path("v.mp4"), cfg)
    assert "信号简史" in m["title"] and "资料来源" in m["description"] and "信息论" in m["tags"]
