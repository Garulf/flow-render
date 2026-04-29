from argparse import ArgumentParser, Namespace
import sys
from typing import Sequence

from config import Config
from plugin import Plugin
from main import main


def get_args(seq: Sequence[str]) -> Namespace:
    parser = ArgumentParser(description="Render a plugin's output")
    parser.add_argument('-p', '--plugin', help="Path to the plugin")
    parser.add_argument('-c', '--config', help="Path to the config file")
    parser.add_argument('-q', '--query', help="Query to run")
    parser.add_argument('-i', action='store_true', help="Use plugin manager")

    return parser.parse_args(seq)


def setup(args: Namespace):
    if args.config:
        config = Config.from_file(args.config)
    elif args.plugin:
        print(args.plugin)
        plugin = Plugin(args.plugin)
        if args.i:
            config = Config(plugin=plugin_manager(plugin=plugin))
        else:
            config = Config(plugin_to_config(plugin, args.query))
    main(config)


if __name__ == '__main__':
    setup(get_args(sys.argv[1:]))
