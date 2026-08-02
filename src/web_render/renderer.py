from pathlib import Path
import jinja2

from .config import Config

DEFAULT_TEMPLATES = Path(__file__).parent / 'templates'
STATIC_DIR = Path(__file__).parent / 'static'
BASE_TEMPLATE = 'base.html'


def render(render_data: Config) -> str:
    search_paths = [Path.cwd(), DEFAULT_TEMPLATES, STATIC_DIR]
    template_loader = jinja2.FileSystemLoader(searchpath=search_paths)
    template_env = jinja2.Environment(loader=template_loader)
    loaded_template = template_env.get_template(BASE_TEMPLATE)

    # Keep legacy templates working by exposing Config fields at top-level.
    return loaded_template.render(
        **render_data.as_dict(),
        render_data=render_data,
        static_url=STATIC_DIR.resolve().as_uri(),
    )


def save_rendered(rendered_template: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(rendered_template)


def render_from_config(config: Config, output_path: str = 'output.html'):
    save_rendered(render(config), output_path)
