import json
from pathlib import Path
from dataclasses import dataclass
from typing import Union


FILENAME = "plugin.json"


@dataclass
class PluginManifest:
    ID: str
    ActionKeyword: str
    Name: str
    Description: str
    Author: str
    Version: str
    Language: str
    Website: str
    IcoPath: str
    ExecuteFileName: str

    @classmethod
    def from_file(cls, path: Union[str, Path]):
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def from_path(cls, path: Union[str, Path]):
        return cls.from_file(Path(path) / FILENAME)

    @property
    def is_v2(self) -> bool:
        return self.Language.lower().endswith("_v2")
