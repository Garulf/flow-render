import io
import zipfile
from pathlib import Path

import httpx
import pytest

from flow_render.plugin_source import resolve_plugin_source, resolve_plugin_path

MANIFEST_BYTES = b'{"ID": "1"}'
MAIN_BYTES = b'print("hi")'


def make_zip_bytes(nested: bool) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        prefix = "MyPlugin/" if nested else ""
        archive.writestr(f"{prefix}plugin.json", MANIFEST_BYTES)
        archive.writestr(f"{prefix}main.py", MAIN_BYTES)
    return buffer.getvalue()


def test_resolve_plugin_source_from_local_zip_at_root(tmp_path):
    zip_path = tmp_path / "plugin.zip"
    zip_path.write_bytes(make_zip_bytes(nested=False))

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    plugin_dir = resolve_plugin_source(str(zip_path), dest_dir)

    assert plugin_dir == dest_dir
    assert (plugin_dir / "plugin.json").read_bytes() == MANIFEST_BYTES


def test_resolve_plugin_source_from_local_zip_nested_in_subfolder(tmp_path):
    zip_path = tmp_path / "plugin.zip"
    zip_path.write_bytes(make_zip_bytes(nested=True))

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    plugin_dir = resolve_plugin_source(str(zip_path), dest_dir)

    assert plugin_dir == dest_dir / "MyPlugin"
    assert (plugin_dir / "plugin.json").read_bytes() == MANIFEST_BYTES


def test_resolve_plugin_source_rejects_non_zip_path(tmp_path):
    not_a_zip = tmp_path / "plugin.txt"
    not_a_zip.write_text("nope")

    with pytest.raises(ValueError):
        resolve_plugin_source(str(not_a_zip), tmp_path / "dest")


def test_resolve_plugin_source_rejects_missing_path():
    with pytest.raises(ValueError):
        resolve_plugin_source("/does/not/exist.zip", Path("/tmp/unused"))


def test_resolve_plugin_source_raises_when_no_plugin_json(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("main.py", MAIN_BYTES)

    zip_path = tmp_path / "plugin.zip"
    zip_path.write_bytes(buffer.getvalue())

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        resolve_plugin_source(str(zip_path), dest_dir)


def test_resolve_plugin_source_downloads_from_url(tmp_path, monkeypatch):
    zip_bytes = make_zip_bytes(nested=False)

    def fake_get(url, timeout, follow_redirects):
        assert url == "https://example.com/plugin.zip"
        assert follow_redirects is True
        return httpx.Response(200, content=zip_bytes, request=httpx.Request("GET", url))

    monkeypatch.setattr("flow_render.plugin_source.httpx.get", fake_get)

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    plugin_dir = resolve_plugin_source("https://example.com/plugin.zip", dest_dir)

    assert (plugin_dir / "plugin.json").read_bytes() == MANIFEST_BYTES


def test_resolve_plugin_path_returns_existing_directory_as_is(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    plugin_dir = tmp_path / "MyPlugin"
    plugin_dir.mkdir()

    assert resolve_plugin_path(str(plugin_dir)) == str(plugin_dir)


def test_resolve_plugin_path_uses_parent_dir_when_given_a_file_inside_it(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    plugin_dir = tmp_path / "Github Quick Launcher-4.0.0"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text("{}")
    pyz = plugin_dir / "Github-Quick-Launcher.pyz"
    pyz.write_bytes(b"")

    assert resolve_plugin_path(str(pyz)) == str(plugin_dir.resolve())


def test_resolve_plugin_path_does_not_use_parent_dir_without_plugin_json(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.chdir(tmp_path)
    plain_dir = tmp_path / "not-a-plugin"
    plain_dir.mkdir()
    stray_file = plain_dir / "readme.txt"
    stray_file.write_text("hi")

    with pytest.raises(FileNotFoundError):
        resolve_plugin_path(str(stray_file))


def test_resolve_plugin_path_finds_exact_name_match_in_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Steam Search").mkdir()

    assert resolve_plugin_path("Steam Search") == str((tmp_path / "Steam Search").resolve())


def test_resolve_plugin_path_finds_versioned_folder_in_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Steam Search-1.5.0").mkdir()

    assert resolve_plugin_path("Steam Search") == str(tmp_path / "Steam Search-1.5.0")


def test_resolve_plugin_path_prefers_cwd_over_flow_launcher_dir(tmp_path, monkeypatch):
    appdata = tmp_path / "AppData"
    flowlauncher_plugins = appdata / "FlowLauncher" / "Plugins"
    flowlauncher_plugins.mkdir(parents=True)
    (flowlauncher_plugins / "Steam Search").mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))

    cwd = tmp_path / "project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    (cwd / "Steam Search").mkdir()

    assert resolve_plugin_path("Steam Search") == str((cwd / "Steam Search").resolve())


def test_resolve_plugin_path_falls_back_to_flow_launcher_dir(tmp_path, monkeypatch):
    appdata = tmp_path / "AppData"
    flowlauncher_plugins = appdata / "FlowLauncher" / "Plugins"
    flowlauncher_plugins.mkdir(parents=True)
    (flowlauncher_plugins / "Steam Search-2.0.0").mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))

    cwd = tmp_path / "project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    assert resolve_plugin_path("Steam Search") == str(flowlauncher_plugins / "Steam Search-2.0.0")


def test_resolve_plugin_path_raises_when_nothing_matches(tmp_path, monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        resolve_plugin_path("Nonexistent Plugin")
