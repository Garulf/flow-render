import json
import sys
from pathlib import Path
import subprocess
from typing import List, Optional, TypedDict
from .plugin_manifest import PluginManifest


class PluginResult(TypedDict):
    Title: str
    SubTitle: str
    IcoPath: str
    Score: int


def sort_results(results: List[PluginResult]) -> List[PluginResult]:
    return sorted(results, key=lambda result: result["Score"], reverse=True)


class Plugin:

    def __init__(self, path: str):
        self.path = path
        self._manifest: Optional[PluginManifest] = None

    @property
    def manifest(self) -> PluginManifest:
        if self._manifest is None:
            self._manifest = PluginManifest.from_path(self.path)
        return self._manifest

    @property
    def execute_path(self) -> str:
        return str(Path(self.path) / self.manifest.ExecuteFileName)

    @property
    def icon_path(self) -> str:
        return str(Path(self.path) / self.manifest.IcoPath)

    def run_plugin(self, query: str) -> List[PluginResult]:
        request = {"method": "query", "parameters": [query]}
        process = subprocess.run(
            [sys.executable, self.execute_path, json.dumps(request)],
            cwd=self.path,
            stdout=subprocess.PIPE
        )
        output = json.loads(process.stdout.decode())
        return sort_results(output["result"])
