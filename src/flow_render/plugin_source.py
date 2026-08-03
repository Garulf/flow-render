import io
import os
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from .result_config import is_url

DOWNLOAD_TIMEOUT_SECONDS = 30


def _fetch_zip_bytes(source: str) -> bytes:
    if is_url(source):
        response = httpx.get(source, timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
        return response.content

    path = Path(source)
    if not path.is_file() or path.suffix.lower() != '.zip':
        raise ValueError(f"'{source}' is not a URL or a local .zip file")
    return path.read_bytes()


def resolve_plugin_source(source: str, dest_dir: Path) -> Path:
    data = _fetch_zip_bytes(source)

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(dest_dir)

    manifest_path = next(dest_dir.rglob('plugin.json'), None)
    if manifest_path is None:
        raise FileNotFoundError(f"No plugin.json found in the extracted contents of '{source}'")
    return manifest_path.parent


def flow_launcher_plugins_dir() -> Optional[Path]:
    """Flow Launcher's own plugin install directory (Windows Roaming AppData).
    None outside Windows, or if APPDATA isn't set."""
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return None
    return Path(appdata) / 'FlowLauncher' / 'Plugins'


def _find_plugin_dir_by_name(base_dir: Optional[Path], name: str) -> Optional[Path]:
    if base_dir is None or not base_dir.is_dir():
        return None
    name_lower = name.lower()
    prefix_matches = []
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.lower() == name_lower:
            return entry
        # Installed Flow Launcher plugin folders are typically named "<Name>-<Version>".
        if entry.name.lower().startswith(f"{name_lower}-"):
            prefix_matches.append(entry)
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    return None


def resolve_plugin_path(value: str) -> str:
    """Resolve a -p/--plugin argument to an actual plugin directory, always as
    an absolute path — Plugin/run_plugin join it with the manifest's
    ExecuteFileName and pass that to a subprocess with cwd set to the plugin
    dir, so a relative path here would get resolved twice and break.

    If `value` is already a directory (relative to cwd or absolute), it's used
    as-is — this is the existing/primary behavior and always wins. Otherwise
    `value` is treated as a plugin name: look for a matching subdirectory of
    the current directory first, then of Flow Launcher's own Plugins
    directory."""
    if Path(value).is_dir():
        return str(Path(value).resolve())

    found = _find_plugin_dir_by_name(Path.cwd(), value)
    if found is None:
        found = _find_plugin_dir_by_name(flow_launcher_plugins_dir(), value)
    if found is None:
        raise FileNotFoundError(
            f"No plugin directory found for '{value}' — checked it as a path, for a "
            f"matching folder in the current directory, and in Flow Launcher's Plugins "
            f"directory."
        )
    return str(found)
