import json
import zipfile
from argparse import Namespace

import pytest

from web_render import cli
from web_render.config import Config

MANIFEST = {
    "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
    "Author": "", "Version": "1.0", "Language": "python", "Website": "",
    "IcoPath": "icon.png", "ExecuteFileName": "main.py",
}
MAIN_PY = (
    'import json\n'
    'print(json.dumps({"result": ['
    '{"Title": "a", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 1}'
    ']}))\n'
)


def test_setup_without_config_or_plugin_exits_with_usage_error():
    args = Namespace(config=None, plugin=None, plugin_url=None, query=None, i=False, css=None, output=None)

    with pytest.raises(SystemExit):
        cli.setup(args)


def test_setup_with_plugin_builds_config_and_renders(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=None, output=None))

    assert isinstance(rendered["config"], Config)
    assert rendered["config"].results[0]["title"] == "a"


def test_setup_with_plugin_url_builds_config_and_renders(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps(MANIFEST))
    (plugin_dir / "main.py").write_text(MAIN_PY)

    zip_path = tmp_path / "plugin.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for file in plugin_dir.iterdir():
            archive.write(file, file.name)

    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=None, plugin_url=str(zip_path), query="q", i=False, css=None, output=None))

    assert isinstance(rendered["config"], Config)
    assert rendered["config"].results[0]["title"] == "a"


def test_setup_with_css_sets_config_css(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=["win11-dark.css"], output=None))

    assert rendered["config"].css == "win11-dark.css"


def test_setup_with_multiple_css_sets_config_css_list(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=["win11-dark.css", "ad-neon.css"], output=None))

    assert rendered["config"].css == ["win11-dark.css", "ad-neon.css"]


def test_setup_passes_output_flag_through_to_main(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=None, output="/tmp/somewhere"))

    assert rendered["output_dir"] == "/tmp/somewhere"


def test_get_args_rejects_plugin_and_plugin_url_together():
    with pytest.raises(SystemExit):
        cli.get_args(["-p", "./plugin", "-u", "./plugin.zip"])


def test_get_args_parses_css_flag():
    args = cli.get_args(["-p", "./plugin", "-s", "win11-dark.css"])

    assert args.css == ["win11-dark.css"]


def test_get_args_parses_multiple_css_flags():
    args = cli.get_args(["-p", "./plugin", "-s", "win11-dark.css", "ad-neon.css"])

    assert args.css == ["win11-dark.css", "ad-neon.css"]


def test_get_args_parses_output_flag():
    args = cli.get_args(["-p", "./plugin", "-o", "/tmp/somewhere"])

    assert args.output == "/tmp/somewhere"


PLUGIN_MANAGER_MANIFEST = {
    "ID": "1", "ActionKeyword": "t", "Name": "Steam Search", "Description": "Search and launch your Steam Game library",
    "Author": "Garulf", "Version": "1.0", "Language": "python", "Website": "",
    "IcoPath": "icon.png", "ExecuteFileName": "main.py",
}


def test_setup_with_plugin_and_i_renders_plugin_manager_view(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(PLUGIN_MANAGER_MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query=None, i=True, css=None, output=None))

    config = rendered["config"]
    assert config.query == "pm install Steam Search"
    assert config.results[0]["title"] == "Steam Search by Garulf"
    assert config.results[0]["subtitle"] == "Search and launch your Steam Game library"


def test_setup_with_plugin_url_and_i_renders_plugin_manager_view(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps(PLUGIN_MANAGER_MANIFEST))
    (plugin_dir / "main.py").write_text(MAIN_PY)

    zip_path = tmp_path / "plugin.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for file in plugin_dir.iterdir():
            archive.write(file, file.name)

    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None: rendered.update(config=config))

    cli.setup(Namespace(config=None, plugin=None, plugin_url=str(zip_path), query=None, i=True, css=None, output=None))

    config = rendered["config"]
    assert config.query == "pm install Steam Search"
    assert config.results[0]["title"] == "Steam Search by Garulf"
    assert config.results[0]["subtitle"] == "Search and launch your Steam Game library"
