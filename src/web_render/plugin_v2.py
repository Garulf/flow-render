import json
import queue
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional

from .plugin_manifest import PluginManifest

TIMEOUT_SECONDS = 30.0


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


def _send(process: subprocess.Popen, message_id: int, method: str, params: list) -> None:
    payload = {"jsonrpc": "2.0", "id": message_id, "method": method, "params": params}
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()


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
        _send(process, 1, "initialize", [{"currentPluginMetadata": _plugin_metadata(manifest, plugin_path, execute_path)}])
        _read_response(process, line_queue, 1, TIMEOUT_SECONDS, stderr_lines, stderr_lock)

        full_query = f"{manifest.ActionKeyword} {query}".strip()
        _send(process, 2, "query", [
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

    return [
        {
            "Title": result.get("title", ""),
            "SubTitle": result.get("subTitle", ""),
            "IcoPath": result.get("icoPath", ""),
            "Score": result.get("score", 0),
        }
        for result in response.get("result", [])
    ]
