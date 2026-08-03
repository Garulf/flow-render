from argparse import ArgumentParser
from pathlib import Path
import sys

import httpx

from .theme_parser import ThemeData, parse_theme_xml, resolve_theme
from .theme_css import theme_to_css

PROJECT_ROOT = Path(__file__).parent.parent.parent
VENDOR_DIR = PROJECT_ROOT / 'themes' / 'xaml'
OUTPUT_DIR = Path(__file__).parent / 'static' / 'themes'
THEMES_API = ('https://api.github.com/repos/Flow-Launcher/Flow.Launcher'
              '/contents/Flow.Launcher/Themes?ref=dev')


def slugify(filename: str) -> str:
    return Path(filename).stem.lower().replace(' ', '-')


def fetch_themes() -> None:
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    listing = httpx.get(THEMES_API, timeout=30)
    listing.raise_for_status()
    for entry in listing.json():
        if not entry['name'].endswith('.xaml'):
            continue
        content = httpx.get(entry['download_url'], timeout=30)
        content.raise_for_status()
        target = VENDOR_DIR / entry['name']
        if not target.exists() or target.read_text() != content.text:
            target.write_text(content.text)
            print(f"vendored {entry['name']}")


def theme_modes(theme: ThemeData) -> list:
    if theme.resources.get('SystemBG') == 'Auto':
        return ['light', 'dark']
    return ['dark' if theme.metadata.get('IsDark') == 'True' else 'light']


def convert_file(xaml_path: Path, base: ThemeData, output_dir: Path) -> list:
    output_dir.mkdir(parents=True, exist_ok=True)
    theme = parse_theme_xml(xaml_path.read_text())
    modes = theme_modes(theme)
    written = []
    for mode in modes:
        resolved = resolve_theme(theme, base, mode)
        apply_mode_background(resolved, mode)
        suffix = f"-{mode}" if len(modes) > 1 else ''
        target = output_dir / f"{slugify(xaml_path.name)}{suffix}.css"
        target.write_text(theme_to_css(resolved, mode))
        written.append(target)
    return written


def apply_mode_background(theme: ThemeData, mode: str) -> None:
    key = 'LightBG' if mode == 'light' else 'DarkBG'
    if key in theme.resources:
        theme.styles.setdefault('WindowBorderStyle', {})['Background'] = theme.resources[key]


def main(argv) -> int:
    parser = ArgumentParser(description="Convert Flow Launcher XAML themes to CSS")
    parser.add_argument('--no-fetch', action='store_true',
                        help="Use vendored xaml without contacting GitHub")
    parser.add_argument('--theme', help="Convert a single theme by file name stem")
    args = parser.parse_args(argv)

    if not args.no_fetch:
        try:
            fetch_themes()
        except httpx.HTTPError as error:
            print(f"fetch failed ({error}); using vendored copies")

    base_path = VENDOR_DIR / 'Base.xaml'
    if not base_path.exists():
        print("Base.xaml missing; run without --no-fetch first", file=sys.stderr)
        return 1
    base = parse_theme_xml(base_path.read_text())

    failures = []
    for xaml_path in sorted(VENDOR_DIR.glob('*.xaml')):
        if xaml_path.name == 'Base.xaml':
            continue
        if args.theme and slugify(xaml_path.name) != slugify(args.theme):
            continue
        try:
            written = convert_file(xaml_path, base, OUTPUT_DIR)
            print(f"{xaml_path.name} -> {', '.join(p.name for p in written)}")
        except Exception as error:
            failures.append(f"{xaml_path.name}: {error}")
    for failure in failures:
        print(f"FAILED {failure}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
