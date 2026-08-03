import json

import pytest

from web_render.plugin import Plugin, sort_results


def test_sort_results_orders_by_score_descending():
    results = [
        {"Title": "low", "SubTitle": "", "IcoPath": "", "Score": 1},
        {"Title": "high", "SubTitle": "", "IcoPath": "", "Score": 90},
        {"Title": "mid", "SubTitle": "", "IcoPath": "", "Score": 50},
    ]

    assert [r["Title"] for r in sort_results(results)] == ["high", "mid", "low"]


def test_run_plugin_returns_sorted_results(tmp_path):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(
        'import json\n'
        'print(json.dumps({"result": ['
        '{"Title": "b", "SubTitle": "", "IcoPath": "", "Score": 10},'
        '{"Title": "a", "SubTitle": "", "IcoPath": "", "Score": 99}'
        ']}))\n'
    )

    results = Plugin(str(tmp_path)).run_plugin("query")

    assert [r["Title"] for r in results] == ["a", "b"]


def _write_manifest_and_script(tmp_path, script: str):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(script)


def test_run_plugin_raises_with_stderr_when_process_exits_nonzero(tmp_path):
    _write_manifest_and_script(
        tmp_path,
        'import sys\n'
        'print("broken dependency traceback here", file=sys.stderr)\n'
        'sys.exit(1)\n',
    )

    with pytest.raises(RuntimeError, match="broken dependency traceback here"):
        Plugin(str(tmp_path)).run_plugin("query")


def test_run_plugin_raises_with_stdout_and_stderr_on_invalid_json(tmp_path):
    _write_manifest_and_script(
        tmp_path,
        'import sys\n'
        'print("not json")\n'
        'print("some warning", file=sys.stderr)\n',
    )

    with pytest.raises(RuntimeError, match="some warning"):
        Plugin(str(tmp_path)).run_plugin("query")
