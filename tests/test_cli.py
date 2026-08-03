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
    args = Namespace(config=None, plugin=None, plugin_url=None, query=None, i=False, css=None, output=None, max_results=3, command=None, width=None, height=None)

    with pytest.raises(SystemExit):
        cli.setup(args)


def test_setup_with_plugin_builds_config_and_renders(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=None, output=None, max_results=3, command=None, width=None, height=None))

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
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=None, plugin_url=str(zip_path), query="q", i=False, css=None, output=None, max_results=3, command=None, width=None, height=None))

    assert isinstance(rendered["config"], Config)
    assert rendered["config"].results[0]["title"] == "a"


def test_setup_with_css_sets_config_css(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=["win11-dark.css"], output=None, max_results=3, command=None, width=None, height=None))

    assert rendered["config"].css == "win11-dark.css"


def test_setup_with_multiple_css_sets_config_css_list(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=["win11-dark.css", "ad-neon.css"], output=None, max_results=3, command=None, width=None, height=None))

    assert rendered["config"].css == ["win11-dark.css", "ad-neon.css"]


def test_setup_passes_output_flag_through_to_main(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=None, output="/tmp/somewhere", max_results=3, command=None, width=None, height=None))

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


def test_get_args_max_results_defaults_to_three():
    args = cli.get_args(["-p", "./plugin"])

    assert args.max_results == 3


def test_get_args_parses_max_results_flag():
    args = cli.get_args(["-p", "./plugin", "-m", "5"])

    assert args.max_results == 5


def test_get_args_width_and_height_default_to_none():
    args = cli.get_args(["-p", "./plugin"])

    assert args.width is None
    assert args.height is None


def test_get_args_parses_width_and_height_flags():
    args = cli.get_args(["-p", "./plugin", "-W", "1600", "-H", "900"])

    assert args.width == 1600
    assert args.height == 900


def test_resolve_canvas_size_prefers_explicit_flags_over_detected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo.css").write_text("/* web-render-canvas: 1080x1080 */\n")
    config = Config(keyword="pm", query="steam", icon="data:image/png;base64,x", css="promo.css")
    args = Namespace(width=1600, height=900)

    assert cli.resolve_canvas_size(config, args) == (1600, 900)


def test_resolve_canvas_size_falls_back_to_css_marker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo.css").write_text("/* web-render-canvas: 1080x1080 */\n")
    config = Config(keyword="pm", query="steam", icon="data:image/png;base64,x", css="promo.css")
    args = Namespace(width=None, height=None)

    assert cli.resolve_canvas_size(config, args) == (1080, 1080)


def test_resolve_canvas_size_is_none_when_no_flag_or_marker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = Config(keyword="pm", query="steam", icon="data:image/png;base64,x")
    args = Namespace(width=None, height=None)

    assert cli.resolve_canvas_size(config, args) == (None, None)


def test_setup_passes_resolved_canvas_size_to_main(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    (tmp_path / "promo.css").write_text("/* web-render-canvas: 1080x1080 */\n")
    monkeypatch.chdir(tmp_path)
    captured = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: captured.update(kwargs))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False,
                        css="promo.css", output=None, max_results=3, command=None, width=None, height=None))

    assert captured["width"] == 1080
    assert captured["height"] == 1080


def test_setup_with_max_results_caps_config_results(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(
        'import json\n'
        'print(json.dumps({"result": ['
        '{"Title": "a", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 3},'
        '{"Title": "b", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 2},'
        '{"Title": "c", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 1}'
        ']}))\n'
    )
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config, output_dir=output_dir))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query="q", i=False, css=None, output=None, max_results=2, command=None, width=None, height=None))

    assert [r["title"] for r in rendered["config"].results] == ["a", "b"]


PLUGIN_MANAGER_MANIFEST = {
    "ID": "1", "ActionKeyword": "t", "Name": "Steam Search", "Description": "Search and launch your Steam Game library",
    "Author": "Garulf", "Version": "1.0", "Language": "python", "Website": "",
    "IcoPath": "icon.png", "ExecuteFileName": "main.py",
}


def test_setup_with_plugin_and_i_renders_plugin_manager_view(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(PLUGIN_MANAGER_MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    rendered = {}
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config))

    cli.setup(Namespace(config=None, plugin=str(tmp_path), plugin_url=None, query=None, i=True, css=None, output=None, max_results=3, command=None, width=None, height=None))

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
    monkeypatch.setattr(cli, "main", lambda config, output_dir=None, **kwargs: rendered.update(config=config))

    cli.setup(Namespace(config=None, plugin=None, plugin_url=str(zip_path), query=None, i=True, css=None, output=None, max_results=3, command=None, width=None, height=None))

    config = rendered["config"]
    assert config.query == "pm install Steam Search"
    assert config.results[0]["title"] == "Steam Search by Garulf"
    assert config.results[0]["subtitle"] == "Search and launch your Steam Game library"


def test_get_args_edit_subcommand_parses_plugin_and_query_and_css():
    args = cli.get_args(["edit", "-p", "./plugin", "-q", "steam", "-s", "ad-neon.css"])

    assert args.command == "edit"
    assert args.plugin == "./plugin"
    assert args.query == "steam"
    assert args.css == ["ad-neon.css"]


def test_get_args_edit_subcommand_parses_max_results():
    args = cli.get_args(["edit", "-p", "./plugin", "-q", "steam", "-m", "3"])

    assert args.max_results == 3


def test_get_args_edit_subcommand_max_results_defaults_to_three():
    args = cli.get_args(["edit", "-p", "./plugin"])

    assert args.max_results == 3


def test_setup_edit_with_query_passes_max_results_to_plugin_to_config(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(
        'import json\n'
        'print(json.dumps({"result": ['
        '{"Title": "a", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 3},'
        '{"Title": "b", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 2},'
        '{"Title": "c", "SubTitle": "", "IcoPath": "data:image/png;base64,x", "Score": 1}'
        ']}))\n'
    )
    captured = {}
    monkeypatch.setattr(cli.edit_server, "run",
                        lambda config, base_css_files, **kw: captured.update(config=config))

    args = Namespace(command="edit", plugin=str(tmp_path), plugin_url=None, query="q",
                     css=None, config=None, i=False, output=None, max_results=2)
    cli.setup(args)

    assert [r["title"] for r in captured["config"].results] == ["a", "b"]


def test_get_args_no_subcommand_has_command_none():
    args = cli.get_args(["-p", "./plugin"])

    assert args.command is None


def test_setup_edit_without_plugin_or_url_exits_with_usage_error():
    args = Namespace(command="edit", plugin=None, plugin_url=None, query=None, css=None,
                     config=None, i=False, output=None, max_results=3)

    with pytest.raises(SystemExit):
        cli.setup(args)


def test_setup_edit_dispatches_to_edit_server_run(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    captured = {}
    monkeypatch.setattr(cli.edit_server, "run",
                        lambda config, base_css_files, **kw: captured.update(
                            config=config, base_css_files=base_css_files))

    args = Namespace(command="edit", plugin=str(tmp_path), plugin_url=None, query=None,
                     css=["ad-neon.css"], config=None, i=False, output=None, max_results=3)
    cli.setup(args)

    assert captured["config"].plugin["Name"] == "Test"
    assert captured["base_css_files"] == ["ad-neon.css"]


def test_setup_edit_with_query_uses_plugin_to_config(tmp_path, monkeypatch):
    (tmp_path / "plugin.json").write_text(json.dumps(MANIFEST))
    (tmp_path / "main.py").write_text(MAIN_PY)
    captured = {}
    monkeypatch.setattr(cli.edit_server, "run",
                        lambda config, base_css_files, **kw: captured.update(config=config))

    args = Namespace(command="edit", plugin=str(tmp_path), plugin_url=None, query="q",
                     css=None, config=None, i=False, output=None, max_results=3)
    cli.setup(args)

    assert captured["config"].results[0]["title"] == "a"


def test_setup_edit_with_plugin_url_extracts_and_dispatches(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps(MANIFEST))
    (plugin_dir / "main.py").write_text(MAIN_PY)

    zip_path = tmp_path / "plugin.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for file in plugin_dir.iterdir():
            archive.write(file, file.name)

    captured = {}
    monkeypatch.setattr(cli.edit_server, "run",
                        lambda config, base_css_files, **kw: captured.update(
                            config=config, base_css_files=base_css_files))

    args = Namespace(command="edit", plugin=None, plugin_url=str(zip_path), query=None,
                     css=None, config=None, i=False, output=None, max_results=3)
    cli.setup(args)

    assert captured["config"].plugin["Name"] == "Test"
