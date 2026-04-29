from __future__ import annotations

import io
import mimetypes
from pathlib import Path
from typing import Any, Optional, TypedDict

from datauri import DataURI
import httpx
from PIL import Image

try:
    import win32con
    import win32gui
    import win32ui
except ImportError:  # pragma: no cover
    win32con = None
    win32gui = None
    win32ui = None

win32con = win32con  # type: ignore[assignment]
win32gui = win32gui  # type: ignore[assignment]
win32ui = win32ui  # type: ignore[assignment]


class ResultConfig(TypedDict):
    title: str
    subtitle: str
    icon: str


def is_url(icon: str) -> bool:
    return icon.startswith('http://') or icon.startswith('https://')


def is_data_uri(icon: str) -> bool:
    return icon.startswith('data:')


def parse_icon_location(icon: str) -> tuple[str, int]:
    # Handles values like C:\Windows\System32\shell32.dll,220
    index = 0
    source = icon.strip().strip('"')
    if ',' in source:
        candidate_path, candidate_index = source.rsplit(',', 1)
        candidate_path = candidate_path.strip().strip('"')
        try:
            index = int(candidate_index.strip())
            source = candidate_path
        except ValueError:
            pass
    return source, index


def _to_data_uri(data: bytes, mime_type: str) -> str:
    return DataURI.make(mime_type, None, True, data)


def get_remote_icon(icon: str) -> str:
    response = httpx.get(icon, timeout=15)
    response.raise_for_status()
    mime_type = response.headers.get('content-type') or 'image/png'
    return _to_data_uri(response.content, mime_type)


def get_file_icon(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or 'application/octet-stream'
    return _to_data_uri(path.read_bytes(), mime_type)


def _hicon_to_png_data(hicon: int, size: int = 64) -> Optional[bytes]:
    if not all([win32con, win32gui, win32ui]) or not hicon:
        return None

    gui: Any = win32gui
    con: Any = win32con
    ui: Any = win32ui

    hdc = gui.GetDC(0)
    hdc_mem = ui.CreateDCFromHandle(hdc)
    hdc_compat = hdc_mem.CreateCompatibleDC()

    bmp = ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(hdc_mem, size, size)
    old_obj = hdc_compat.SelectObject(bmp)

    try:
        gui.DrawIconEx(
            hdc_compat.GetSafeHdc(),
            0,
            0,
            hicon,
            size,
            size,
            0,
            None,
            con.DI_NORMAL,
        )

        bmp_info = bmp.GetInfo()
        bmp_str = bmp.GetBitmapBits(True)
        image = Image.frombuffer(
            'RGBA',
            (bmp_info['bmWidth'], bmp_info['bmHeight']),
            bmp_str,
            'raw',
            'BGRA',
            0,
            1,
        )
        # Convert from Windows bottom-up bitmap origin.
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        with io.BytesIO() as buffer:
            image.save(buffer, format='PNG')
            return buffer.getvalue()
    finally:
        hdc_compat.SelectObject(old_obj)
        gui.DeleteObject(bmp.GetHandle())
        hdc_compat.DeleteDC()
        hdc_mem.DeleteDC()
        gui.ReleaseDC(0, hdc)


def get_windows_icon_preview(path: str, index: int = 0) -> Optional[str]:
    if not all([win32con, win32gui, win32ui]):
        return None

    gui: Any = win32gui
    large = []
    small = []
    try:
        large, small = gui.ExtractIconEx(path, index)
        icon_handles = [h for h in (large or []) + (small or []) if h]
        hicon = icon_handles[0] if icon_handles else None
        if not hicon:
            return None

        png_data = _hicon_to_png_data(hicon, size=64)
        return _to_data_uri(png_data, 'image/png') if png_data else None
    except Exception:
        return None
    finally:
        # Ensure all icon handles allocated by Windows are released.
        try:
            for h in (large or []):
                if h:
                    gui.DestroyIcon(h)
            for h in (small or []):
                if h:
                    gui.DestroyIcon(h)
        except Exception:
            pass


def resolve_icon(icon: str, base_path: Optional[str] = None) -> str:
    if not icon:
        return icon
    if is_data_uri(icon):
        return icon
    if is_url(icon):
        try:
            return get_remote_icon(icon)
        except Exception:
            return icon

    source, index = parse_icon_location(icon)
    source_path = Path(source)
    if not source_path.is_absolute() and base_path:
        source_path = Path(base_path) / source_path
    source_path = source_path.expanduser()

    if source_path.exists() and source_path.is_file():
        suffix = source_path.suffix.lower()
        if suffix in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.svg'}:
            try:
                return get_file_icon(source_path)
            except Exception:
                return icon

        if suffix in {'.exe', '.dll', '.icl', '.cpl', '.scr', '.lnk'}:
            preview = get_windows_icon_preview(str(source_path), index=index)
            return preview or icon

    # Support icon locations referencing existing binaries even if path had no extension parsing hit.
    if source_path.exists():
        preview = get_windows_icon_preview(str(source_path), index=index)
        if preview:
            return preview

    return icon