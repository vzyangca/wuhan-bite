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
