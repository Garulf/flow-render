import json

from web_render.config import Config, plugin_to_config
from web_render.plugin import Plugin


def make_config(**overrides):
    defaults = {
        "keyword": "pm",
        "query": "steam",
        "icon": "data:image/png;base64,x",
        "results": [
            {"title": "Steam Search", "subtitle": "sub", "icon": "data:image/png;base64,y"},
        ],
    }
    defaults.update(overrides)
    return Config(**defaults)


def test_suggested_query_completes_matching_result_title():
    config = make_config()

    assert config.query_suggestion == "pm steam"


def test_suggested_query_empty_when_query_not_in_title():
    config = make_config(query="unrelated")

    assert config.query_suggestion == ""


def test_suggested_query_empty_when_no_results():
    config = make_config(results=[])

    assert config.query_suggestion == ""


def test_as_dict_does_not_print(capsys):
    make_config().as_dict()

    assert capsys.readouterr().out == ""


def test_from_file_does_not_print(tmp_path, capsys):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "keyword": "pm",
        "query": "steam",
        "icon": "data:image/png;base64,x",
        "results": [],
    }))

    Config.from_file(str(config_file))

    assert capsys.readouterr().out == ""


def test_from_file_round_trips_through_save(tmp_path):
    original = make_config()
    saved = tmp_path / "config.json"
    original.save_to_file(str(saved))

    assert Config.from_file(str(saved)) == original


def test_css_files_empty_when_css_not_set():
    config = make_config()

    assert config.css_files == []


def test_css_files_wraps_single_stylesheet():
    config = make_config(css="win11-dark.css")

    assert config.css_files == ["win11-dark.css"]


def test_css_files_returns_list_as_is():
    config = make_config(css=["win11-dark.css", "ad-neon.css"])

    assert config.css_files == ["win11-dark.css", "ad-neon.css"]


def test_plugin_to_config_caps_and_orders_results(tmp_path, monkeypatch):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    plugin = Plugin(str(tmp_path))
    monkeypatch.setattr(Plugin, "run_plugin", lambda self, query: [
        {"Title": "first", "SubTitle": "", "IcoPath": "data:image/png;base64,a", "Score": 90},
        {"Title": "second", "SubTitle": "", "IcoPath": "data:image/png;base64,b", "Score": 50},
    ])

    config = plugin_to_config(plugin, "query", max_results=1)

    assert [r["title"] for r in config.results] == ["first"]
    assert config.keyword == "t"
    assert config.max_results == 1
