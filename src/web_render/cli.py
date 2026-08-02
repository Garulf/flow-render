from argparse import ArgumentParser, Namespace
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .config import Config, plugin_manager_config, plugin_to_config
from .plugin import Plugin
from .plugin_source import resolve_plugin_source
from .main import main


def get_args(seq: Sequence[str]) -> Namespace:
    parser = ArgumentParser(description="Render a plugin's output")
    plugin_group = parser.add_mutually_exclusive_group()
    plugin_group.add_argument('-p', '--plugin', help="Path to the plugin")
    plugin_group.add_argument('-u', '--plugin-url', help="URL or local path to a plugin .zip to download/extract and use")
    parser.add_argument('-c', '--config', help="Path to the config file")
    parser.add_argument('-q', '--query', help="Query to run")
    parser.add_argument('-i', action='store_true', help="Use plugin manager")

    return parser.parse_args(seq)


def config_from_plugin(plugin: Plugin, args: Namespace) -> Config:
    if args.i:
        return plugin_manager_config(plugin)
    return plugin_to_config(plugin, args.query)


def build_config(args: Namespace) -> Config:
    if args.config:
        return Config.from_file(args.config)
    if args.plugin_url:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_path = resolve_plugin_source(args.plugin_url, Path(tmp_dir))
            return config_from_plugin(Plugin(str(plugin_path)), args)
    return config_from_plugin(Plugin(args.plugin), args)


def setup(args: Namespace):
    if not args.config and not args.plugin and not args.plugin_url:
        sys.exit("Provide a config file (-c), a plugin path (-p), or a plugin zip (-u). See --help.")
    main(build_config(args))


def run():
    setup(get_args(sys.argv[1:]))


if __name__ == '__main__':
    run()
