from dataclasses import dataclass, field, asdict
from typing import List, Optional, Union
import json
from pathlib import Path

from .result_config import resolve_icon
from .plugin import Plugin, PluginResult

PLUGIN_MANAGER_ICON = (
    "https://github.com/Flow-Launcher/Flow.Launcher/blob/dev/Plugins/"
    "Flow.Launcher.Plugin.PluginsManager/Images/pluginsmanager.png?raw=true"
)


@dataclass
class Config:
    keyword: str
    query: str
    icon: str
    max_results: int = 3
    selection: int = 0
    results: List[PluginResult] = field(default_factory=list)
    css: Optional[Union[str, List[str]]] = None
    query_suggestion: Optional[str] = None
    plugin: Optional[dict] = None

    def __post_init__(self):
        if not self.query_suggestion:
            self.query_suggestion = self.suggested_query

    @property
    def css_files(self) -> List[str]:
        if not self.css:
            return []
        if isinstance(self.css, str):
            return [self.css]
        return list(self.css)

    @property
    def visible_results(self) -> List[PluginResult]:
        return self.results[:self.max_results]

    @property
    def scrollbar_thumb_percent(self) -> float:
        if not self.results or self.max_results >= len(self.results):
            return 100.0
        return max(10.0, self.max_results / len(self.results) * 100)

    @property
    def suggested_query(self) -> str:
        if not self.query or not self.results:
            return ""
        title = self.selected_result["title"]
        if not title.lower().startswith(self.query.lower()):
            return ""
        if self.keyword:
            return f"{self.keyword} {title}"
        return title

    @property
    def full_query(self) -> str:
        if self.keyword:
            return f"{self.keyword} {self.query}"
        return self.query

    @property
    def selected_result(self) -> Optional[PluginResult]:
        return self.results[self.selection] if self.results else None

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        return cls(**data)

    @classmethod
    def from_file(cls, path: str) -> 'Config':
        with open(path, 'r') as f:
            data = json.load(f)
        base_path = str(Path(path).parent.resolve())
        data["icon"] = resolve_icon(data.get("icon", ""), base_path=base_path)
        for result in data.get("results", []):
            result["icon"] = resolve_icon(result.get("icon", ""), base_path=base_path)
        return cls(**data)

    def save_to_file(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.as_dict(), f, indent=4)


MAX_STORED_RESULTS = 20


def plugin_to_config(plugin: Plugin, query: str, max_results: int = 3) -> Config:
    results = plugin.run_plugin(query)
    return Config(
        keyword=plugin.manifest.ActionKeyword,
        query=query,
        icon=resolve_icon(plugin.icon_path, base_path=plugin.path),
        max_results=max_results,
        plugin=asdict(plugin.manifest),
        results=[
            {
                "title": result["Title"],
                "subtitle": result["SubTitle"],
                "icon": resolve_icon(result["IcoPath"], base_path=plugin.path)
            }
            for result in results[:MAX_STORED_RESULTS]
        ]
    )


def plugin_manager_config(plugin: Plugin) -> Config:
    install_query = f"pm install {plugin.manifest.Name}"
    return Config(
        keyword="",
        query=install_query,
        query_suggestion=install_query,
        icon=resolve_icon(PLUGIN_MANAGER_ICON),
        plugin=asdict(plugin.manifest),
        results=[
            {
                "title": f"{plugin.manifest.Name} by {plugin.manifest.Author}",
                "subtitle": plugin.manifest.Description,
                "icon": resolve_icon(plugin.icon_path, base_path=plugin.path)
            }
        ]
    )
