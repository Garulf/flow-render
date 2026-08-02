import json
import queue
import subprocess
import sys
import threading
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from .plugin_manifest import PluginManifest

TIMEOUT_SECONDS = 30.0
SEARCH_PRECISION = 50


class PluginV2Error(RuntimeError):
    pass


def _reader_thread(stdout, line_queue: "queue.Queue[Optional[str]]") -> None:
    for line in iter(stdout.readline, ""):
        line_queue.put(line)
    line_queue.put(None)


def _stderr_collector(stderr, buffer: List[str], lock: threading.Lock) -> None:
    for line in iter(stderr.readline, ""):
        with lock:
            buffer.append(line)


def _send(process: subprocess.Popen, payload: dict) -> None:
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()


def _send_request(process: subprocess.Popen, message_id: int, method: str, params: list) -> None:
    _send(process, {"jsonrpc": "2.0", "id": message_id, "method": method, "params": params})


def _fuzzy_search(query: str, text: str) -> dict:
    if not query:
        return {"success": True, "score": 100, "rawScore": 100, "matchData": [], "searchPrecision": SEARCH_PRECISION}
    if not text:
        return {"success": False, "score": 0, "rawScore": 0, "matchData": [], "searchPrecision": SEARCH_PRECISION}

    query_lower = query.lower()
    text_lower = text.lower()
    index = text_lower.find(query_lower)
    if index != -1:
        match_data = list(range(index, index + len(query_lower)))
        score = min(100, 60 + int(40 * len(query_lower) / len(text_lower)) + (20 if index == 0 else 0))
    else:
        match_data = []
        score = int(SequenceMatcher(None, query_lower, text_lower).ratio() * 100)

    return {
        "success": score >= SEARCH_PRECISION,
        "score": score,
        "rawScore": score,
        "matchData": match_data,
        "searchPrecision": SEARCH_PRECISION,
    }


def _handle_inbound_request(process: subprocess.Popen, message: dict) -> None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", message.get("parameters", []))

    if method == "FuzzySearch":
        query, text = (list(params) + ["", ""])[:2]
        result: Any = _fuzzy_search(str(query or ""), str(text or ""))
    else:
        result = {}

    if request_id is not None:
        _send(process, {"id": request_id, "result": result, "error": None})


def _stderr_detail(stderr_lines: List[str], lock: threading.Lock) -> str:
    with lock:
        text = "".join(stderr_lines).strip()
    return f": {text}" if text else ""


def _read_response(
    process: subprocess.Popen,
    line_queue: "queue.Queue[Optional[str]]",
    message_id: int,
    timeout: float,
    stderr_lines: List[str],
    stderr_lock: threading.Lock,
) -> dict:
    try:
        while True:
            line = line_queue.get(timeout=timeout)
            if line is None:
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
                raise PluginV2Error(f"Plugin process exited before responding{_stderr_detail(stderr_lines, stderr_lock)}")
            line = line.strip()
            if not line:
                continue
            message = json.loads(line)
            if "method" in message:
                _handle_inbound_request(process, message)
                continue
            if message.get("id") == message_id:
                if message.get("error") is not None:
                    raise PluginV2Error(f"Plugin returned an error: {message['error']}")
                return message["result"]
    except queue.Empty:
        raise PluginV2Error(f"Timed out waiting for a response to request {message_id}{_stderr_detail(stderr_lines, stderr_lock)}")


def _plugin_metadata(manifest: PluginManifest, plugin_path: str, execute_path: str) -> dict:
    return {
        "id": manifest.ID,
        "name": manifest.Name,
        "author": manifest.Author,
        "version": manifest.Version,
        "language": manifest.Language.lower(),
        "description": manifest.Description,
        "website": manifest.Website,
        "disabled": False,
        "pluginDirectory": plugin_path,
        "actionKeywords": [manifest.ActionKeyword],
        "actionKeyword": manifest.ActionKeyword,
        "executeFilePath": execute_path,
        "icoPath": manifest.IcoPath,
    }


def _first(result: dict, *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = result.get(key)
        if value is not None:
            return value
    return default


def _normalize_result(result: dict) -> Dict[str, Any]:
    # V2 plugin SDKs disagree on result key casing: flogin uses camelCase
    # (title/subTitle/icoPath/score), pyflowlauncher uses PascalCase
    # (Title/SubTitle/IcoPath/Score, matching the original V1 protocol).
    return {
        "Title": _first(result, "title", "Title"),
        "SubTitle": _first(result, "subTitle", "SubTitle"),
        "IcoPath": _first(result, "icoPath", "IcoPath"),
        "Score": _first(result, "score", "Score", default=0),
    }


def run_plugin(plugin_path: str, execute_path: str, manifest: PluginManifest, query: str) -> List[Dict[str, Any]]:
    process = subprocess.Popen(
        [sys.executable, execute_path],
        cwd=plugin_path,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    line_queue: "queue.Queue[Optional[str]]" = queue.Queue()
    stdout_reader = threading.Thread(target=_reader_thread, args=(process.stdout, line_queue), daemon=True)
    stdout_reader.start()

    stderr_lines: List[str] = []
    stderr_lock = threading.Lock()
    stderr_reader = threading.Thread(target=_stderr_collector, args=(process.stderr, stderr_lines, stderr_lock), daemon=True)
    stderr_reader.start()

    try:
        _send_request(process, 1, "initialize", [{"currentPluginMetadata": _plugin_metadata(manifest, plugin_path, execute_path)}])
        _read_response(process, line_queue, 1, TIMEOUT_SECONDS, stderr_lines, stderr_lock)

        full_query = f"{manifest.ActionKeyword} {query}".strip()
        _send_request(process, 2, "query", [
            {"search": query, "rawQuery": full_query, "isReQuery": False, "actionKeyword": manifest.ActionKeyword},
            {},
        ])
        response = _read_response(process, line_queue, 2, TIMEOUT_SECONDS, stderr_lines, stderr_lock)
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        stderr_reader.join(timeout=2)

    return [_normalize_result(result) for result in response.get("result", [])]
