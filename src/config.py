from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json
from pathlib import Path

from result_config import resolve_icon
from plugin import Plugin, PluginResult


@dataclass
class Config:
    keyword: str
    query: str
    icon: str
    max_results: int = 3
    selection: int = 0
    results: List[PluginResult] = field(default_factory=list)
    css: Optional[str] = None
    query_suggestion: Optional[str] = None

    def __post_init__(self):
        if not self.query_suggestion:
            self.query_suggestion = self.create_suggestion

    @property
    def create_suggestion(self) -> str:
        if self.query.lower() in self.selected_result["title"].lower():
            return self.full_query
        return ""

    @property
    def full_query(self) -> str:
        if self.keyword:
            return f"{self.keyword} {self.query}"
        return self.query

    @property
    def selected_result(self) -> PluginResult:
        return self.results[self.selection] if self.results else {}

    def as_dict(self):
        print(json.dumps(asdict(self), indent=4))
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
        print(data["query"])
        return cls(
            **data
        )

    def save_to_file(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.as_dict(), f, indent=4)


def plugin_to_config(plugin: Plugin, query: str, max_results: int = 3) -> Config:
    output = plugin.run_plugin(query)
    plugin_base_path = plugin.path
    return Config(
        keyword=plugin.manifest.ActionKeyword,
        query=query,
        icon=resolve_icon(plugin.icon_path, base_path=plugin_base_path),
        max_results=max_results,
        results=[
            {
                "title": item["Title"],
                "subtitle": item["SubTitle"],
                "icon": resolve_icon(item["IcoPath"], base_path=plugin_base_path)
            }
            for item in sort_results(output["result"])[:max_results]
        ]
    )



def plugin_manager(plugin: Plugin) -> Config:
    return Config(
        query=f"pm install {plugin.manifest.Name}",
        query_suggestion=f"pm install {plugin.manifest.Name}",
        icon=resolve_icon("https://github.com/Flow-Launcher/Flow.Launcher/blob/dev/Plugins/Flow.Launcher.Plugin.PluginsManager/Images/pluginsmanager.png?raw=true"),
        max_results=3,
        results=[
            {
                "title": f"{plugin.manifest.Name} by {plugin.manifest.Author}",
                "subtitle": plugin.manifest.Description,
                "icon": resolve_icon(plugin.icon_path, base_path=plugin.path)
            }
        ]
    )
