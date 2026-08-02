import json

import pytest

from web_render.plugin import Plugin
from web_render.plugin_v2 import PluginV2Error

FAKE_V2_PLUGIN = '''
import json
import sys


def send(message_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message_id, "result": result, "error": None}) + "\\n")
    sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    message = json.loads(line)
    if message.get("method") == "initialize":
        send(message["id"], {"hide": False})
    elif message.get("method") == "query":
        send(message["id"], {
            "debugMessage": "",
            "settingsChange": {},
            "result": [
                {"title": "b", "subTitle": "", "icoPath": "", "score": 10},
                {"title": "a", "subTitle": "", "icoPath": "", "score": 99},
            ],
        })
'''


def make_manifest(tmp_path, language: str):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": language, "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(FAKE_V2_PLUGIN)


def test_run_plugin_v2_returns_sorted_results(tmp_path):
    make_manifest(tmp_path, "python_v2")

    results = Plugin(str(tmp_path)).run_plugin("query")

    assert [r["Title"] for r in results] == ["a", "b"]


def test_run_plugin_v2_unsupported_language_raises(tmp_path):
    make_manifest(tmp_path, "javascript_v2")

    with pytest.raises(NotImplementedError):
        Plugin(str(tmp_path)).run_plugin("query")


CRASHING_V2_PLUGIN = '''
import sys

print("boom: something went wrong", file=sys.stderr)
sys.exit(1)
'''


def test_run_plugin_v2_surfaces_stderr_on_crash(tmp_path):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python_v2", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(CRASHING_V2_PLUGIN)

    with pytest.raises(PluginV2Error, match="boom: something went wrong"):
        Plugin(str(tmp_path)).run_plugin("query")


ERRORING_V2_PLUGIN = '''
import json
import sys

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    message = json.loads(line)
    sys.stdout.write(json.dumps({
        "jsonrpc": "2.0",
        "id": message["id"],
        "error": {"code": -32000, "message": "plugin blew up"},
    }) + "\\n")
    sys.stdout.flush()
'''


def test_run_plugin_v2_raises_on_real_error(tmp_path):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python_v2", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(ERRORING_V2_PLUGIN)

    with pytest.raises(PluginV2Error, match="plugin blew up"):
        Plugin(str(tmp_path)).run_plugin("query")


NOISY_STDERR_V2_PLUGIN = '''
import json
import sys


def send(message_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message_id, "result": result, "error": None}) + "\\n")
    sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    message = json.loads(line)
    if message.get("method") == "initialize":
        send(message["id"], {"hide": False})
    elif message.get("method") == "query":
        # Write more than a pipe buffer's worth of stderr before responding.
        # If the caller isn't draining stderr concurrently, this write blocks
        # forever and the caller sees a false "timed out" instead of a result.
        for _ in range(20000):
            print("noisy log line", file=sys.stderr)
        send(message["id"], {
            "debugMessage": "",
            "settingsChange": {},
            "result": [{"title": "a", "subTitle": "", "icoPath": "", "score": 1}],
        })
'''


def test_run_plugin_v2_does_not_deadlock_on_noisy_stderr(tmp_path):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python_v2", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(NOISY_STDERR_V2_PLUGIN)

    results = Plugin(str(tmp_path)).run_plugin("query")

    assert [r["Title"] for r in results] == ["a"]


# Mimics pyflowlauncher's FlowLauncherV2 launcher: a plugin that calls back
# into the host's "FuzzySearch" method (an inbound request, not a reply to
# one of our own) for every candidate before deciding whether to include it.
# If the host never answers, real plugins built this way silently swallow
# the resulting timeout and return an empty result list.
CALLBACK_V2_PLUGIN = '''
import json
import sys

_next_id = [100]


def send(payload):
    sys.stdout.write(json.dumps(payload) + "\\n")
    sys.stdout.flush()


def fuzzy_search(query, text):
    _next_id[0] += 1
    request_id = _next_id[0]
    send({"jsonrpc": "2.0", "id": request_id, "method": "FuzzySearch", "params": [query, text]})
    while True:
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("host closed the stream")
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        if message.get("id") == request_id and "method" not in message:
            return message["result"]


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    message = json.loads(line)
    if message.get("method") == "initialize":
        send({"jsonrpc": "2.0", "id": message["id"], "result": {"hide": False}, "error": None})
    elif message.get("method") == "query":
        query = message["params"][0]["search"]
        results = []
        for candidate in ["doom eternal", "unrelated game"]:
            match = fuzzy_search(query, candidate)
            if match["success"]:
                results.append({"title": candidate, "subTitle": "", "icoPath": "", "score": match["score"]})
        send({
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {"debugMessage": "", "settingsChange": {}, "result": results},
            "error": None,
        })
'''


def test_run_plugin_v2_answers_inbound_fuzzy_search_callbacks(tmp_path):
    manifest = {
        "ID": "1", "ActionKeyword": "t", "Name": "Test", "Description": "",
        "Author": "", "Version": "1.0", "Language": "python_v2", "Website": "",
        "IcoPath": "icon.png", "ExecuteFileName": "main.py",
    }
    (tmp_path / "plugin.json").write_text(json.dumps(manifest))
    (tmp_path / "main.py").write_text(CALLBACK_V2_PLUGIN)

    results = Plugin(str(tmp_path)).run_plugin("doom")

    assert [r["Title"] for r in results] == ["doom eternal"]
