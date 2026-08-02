import json
from argparse import Namespace

import pytest

from web_render import cli
from web_render.config import Config


def test_setup_without_config_or_plugin_exits_with_usage_error():
    args = Namespace(config=None, plugin=None, query=None, i=False)

    with pytest.raises(SystemExit):
        cli.setup(args)


def test_setup_with_plugin_builds_config_and_renders(tmp_path, monkeypatch):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(
        'import json\n'
        'print(json.dumps({"result": ['
        '{"Title": "a", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 1}'
        ']}))\n'
    )
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config: rendered.update(config=config))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), query="q", i=False))

    assert isinstance(rendered["config"], Config)
    assert rendered["config"].results[0]["title"] == "a"
