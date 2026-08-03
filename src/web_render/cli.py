from argparse import ArgumentParser, Namespace
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from . import edit_server
from .config import Config, plugin_manager_config, plugin_to_config
from .plugin import Plugin
from .plugin_source import resolve_plugin_source
from .renderer import detect_canvas_size
from .main import main


def add_common_arguments(parser: ArgumentParser) -> None:
    plugin_group = parser.add_mutually_exclusive_group()
    plugin_group.add_argument('-p', '--plugin', help="Path to the plugin")
    plugin_group.add_argument('-u', '--plugin-url', help="URL or local path to a plugin .zip to download/extract and use")
    parser.add_argument('-q', '--query', help="Query to run")
    parser.add_argument('-s', '--css', nargs='+', help="Stylesheet(s) to render with (e.g. win11-dark.css ad-neon.css)")
    parser.add_argument('-m', '--max-results', type=int, default=3, help="Maximum number of results to render (only applies with -p/-u; default: 3)")


def get_args(seq: Sequence[str]) -> Namespace:
    parser = ArgumentParser(description="Render a plugin's output")
    add_common_arguments(parser)
    parser.add_argument('-c', '--config', help="Path to the config file")
    parser.add_argument('-i', action='store_true', help="Use plugin manager")
    parser.add_argument('-o', '--output', help="Directory to save the rendered PNG in (defaults to a per-user data directory)")
    parser.add_argument('-W', '--width', type=int, help="Screenshot width in px (defaults to the css theme's canvas size, if any, else 1280)")
    parser.add_argument('-H', '--height', type=int, help="Screenshot height in px (defaults to the css theme's canvas size, if any, else 720)")

    subparsers = parser.add_subparsers(dest='command')
    edit_parser = subparsers.add_parser(
        'edit', help="Open a local browser-based editor for authoring theme CSS")
    add_common_arguments(edit_parser)

    return parser.parse_args(seq)


def config_from_plugin(plugin: Plugin, args: Namespace) -> Config:
    config = plugin_manager_config(plugin) if args.i else plugin_to_config(plugin, args.query, max_results=args.max_results)
    if args.css:
        css = args.css
        if isinstance(css, list) and len(css) == 1:
            css = css[0]
        config.css = css
    return config


def build_config(args: Namespace) -> Config:
    if args.config:
        return Config.from_file(args.config)
    if args.plugin_url:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_path = resolve_plugin_source(args.plugin_url, Path(tmp_dir))
            return config_from_plugin(Plugin(str(plugin_path)), args)
    return config_from_plugin(Plugin(args.plugin), args)


def config_for_edit_path(plugin_path: str, query: Optional[str], max_results: int = 3) -> Config:
    plugin = Plugin(plugin_path)
    if query is None:
        return plugin_manager_config(plugin)
    return plugin_to_config(plugin, query, max_results=max_results)


def run_edit(args: Namespace) -> None:
    if not args.plugin and not args.plugin_url:
        sys.exit("Edit mode requires a plugin path (-p) or plugin zip (-u). See --help.")
    if args.plugin_url:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_path = str(resolve_plugin_source(args.plugin_url, Path(tmp_dir)))
            config = config_for_edit_path(plugin_path, args.query, args.max_results)
            edit_server.run(config, args.css or [])
        return
    config = config_for_edit_path(args.plugin, args.query, args.max_results)
    edit_server.run(config, args.css or [])


def resolve_canvas_size(config: Config, args: Namespace):
    width, height = args.width, args.height
    if width and height:
        return width, height
    detected = detect_canvas_size(config.css_files)
    if detected:
        return width or detected[0], height or detected[1]
    return width, height


def setup(args: Namespace):
    if args.command == 'edit':
        run_edit(args)
        return
    if not args.config and not args.plugin and not args.plugin_url:
        sys.exit("Provide a config file (-c), a plugin path (-p), or a plugin zip (-u). See --help.")
    config = build_config(args)
    width, height = resolve_canvas_size(config, args)
    main(config, args.output, width=width, height=height)


def run():
    setup(get_args(sys.argv[1:]))


if __name__ == '__main__':
    run()
