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
