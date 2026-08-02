from argparse import ArgumentParser, Namespace
import sys
from typing import Sequence

from .config import Config, plugin_manager_config, plugin_to_config
from .plugin import Plugin
from .main import main


def get_args(seq: Sequence[str]) -> Namespace:
    parser = ArgumentParser(description="Render a plugin's output")
    parser.add_argument('-p', '--plugin', help="Path to the plugin")
    parser.add_argument('-c', '--config', help="Path to the config file")
    parser.add_argument('-q', '--query', help="Query to run")
    parser.add_argument('-i', action='store_true', help="Use plugin manager")

    return parser.parse_args(seq)


def build_config(args: Namespace) -> Config:
    if args.config:
        return Config.from_file(args.config)
    plugin = Plugin(args.plugin)
    if args.i:
        return plugin_manager_config(plugin)
    return plugin_to_config(plugin, args.query)


def setup(args: Namespace):
    if not args.config and not args.plugin:
        sys.exit("Provide a config file (-c) or a plugin path (-p). See --help.")
    main(build_config(args))


def run():
    setup(get_args(sys.argv[1:]))


if __name__ == '__main__':
    run()
