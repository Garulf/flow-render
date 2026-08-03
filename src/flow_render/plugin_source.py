import io
import zipfile
from pathlib import Path

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
