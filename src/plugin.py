import json
import sys
from pathlib import Path
import subprocess
from typing import Dict, List, Optional, TypedDict
from plugin_manifest import PluginManifest


class PluginResult(TypedDict):
    Title: str
    SubTitle: str
    IcoPath: str
    Score: int


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

    @property
    def action_keyword(self) -> str:
        return "" if self.manifest.ActionKeyword == "*" else self.manifest.ActionKeyword
    
    @property
    def has_global_action_keyword(self) -> bool:
        return self.manifest.ActionKeyword == "*"

    def full_query(self, query: str):
        if self.has_global_action_keyword:
            return query
        return f"{self.action_keyword} {query}"

    def run_plugin(self, query: str) -> List[PluginResult]:
        request = {"method": "query", "parameters": [query]}
        p = subprocess.run(
            [sys.executable, self.execute_path, json.dumps(request)],
            cwd=self.path,
            stdout=subprocess.PIPE
        )
        output = json.loads(p.stdout.decode())
        return sort_results(output["result"])


    def sort_results(results: List[PluginResult]) -> List[Dict]:
        return sorted(results, key=lambda x: x["Score"], reverse=True)




