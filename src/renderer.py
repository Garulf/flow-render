from pathlib import Path
from typing import Dict, List, Optional
import jinja2
import tempfile

from config import Config

DEFAULT_TEMPLATES = './src/templates'
BASE_TEMPLATE = 'base.html'

def render(render_data: Config) -> str:
    templates_paths = [DEFAULT_TEMPLATES, Path.cwd()]
    template_loader = jinja2.FileSystemLoader(searchpath=templates_paths)
    template_env = jinja2.Environment(loader=template_loader)
    template_env.globals.update(render_data=render_data)

    loaded_template = template_env.get_template(BASE_TEMPLATE)

    return loaded_template.render()


def save_rendered(rendered_template: str, output_path: str) -> None:
    print("Saving rendered template to", output_path)
    with open(output_path, 'w') as f:
        f.write(rendered_template)


def render_from_config(config: Config):
    rendered = render(
        config
    )
    save_rendered(rendered, 'output.html')
