# flow-render

Renders a Flow Launcher search-result mockup to HTML, screenshots it headlessly with
Playwright, and crops the result to a transparent PNG — useful for generating plugin
screenshots for READMEs and store listings without staging a real launcher window.

![example output](example/output.png)

## How it works

1. A `Config` (from a JSON file, or built by running a real plugin) describes the
   search bar and its results.
2. `renderer.py` renders `templates/base.html` with Jinja2 into a temporary
   `output.html`.
3. `screenshot.py` loads that file in headless Chromium and screenshots it with a
   transparent background.
4. `image.py` crops to the smallest bounding box and writes
   `output_<timestamp>_<id>.png` to the output directory.

Intermediate build files live in a temp directory that's cleaned up automatically
after each run — nothing is left behind wherever you happen to invoke the CLI from.
The final PNG defaults to a per-user data directory (`%LOCALAPPDATA%\flow-render\output`
on Windows, `~/Library/Application Support/flow-render/output` on macOS,
`$XDG_DATA_HOME/flow-render/output` or `~/.local/share/flow-render/output` on Linux) and
accumulates there across runs; override it per-run with `-o`/`--output`.

## Requirements

- Python 3.10+
- Chromium via Playwright (installed automatically by the run scripts)

## Install

Install as a standalone CLI with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install .
playwright install chromium
flow-render -c ./example/config.json
```

## Usage

### Linux / macOS / WSL

```bash
make run CONFIG=./example/config.json
```

Other targets and variables:

```bash
make help
make run PLUGIN=./path/to/plugin QUERY=test
make run PLUGIN_MANAGER=1 PLUGIN=./path/to/plugin
make run CONFIG=./example/config.json SKIP_PLAYWRIGHT=1   # skip the Chromium install step
```

`make` creates `.venv`, installs the package with `uv pip install -e .`, and installs
Chromium on first run; later runs reuse the existing venv.

### Windows

```powershell
.\run.ps1 -c .\example\config.json
```

`run.ps1` does the same venv + Playwright bootstrap, prompting for elevation only if
the Chromium install needs it, then forwards all arguments to the CLI.

### Direct CLI

```bash
flow-render -c ./example/config.json
```

| Flag | Meaning |
| --- | --- |
| `-c`, `--config` | Path to a config JSON file |
| `-p`, `--plugin` | Path to a Flow Launcher plugin directory (read via its `plugin.json`) |
| `-u`, `--plugin-url` | URL or local path to a plugin `.zip`; extracted to a temp dir and used like `-p` |
| `-q`, `--query` | Query to run against the plugin |
| `-i` | Render the plugin-manager "pm install" view for the given plugin (works with `-p` or `-u`) instead of running a query |
| `-s`, `--css` | Stylesheet(s) to render with, e.g. `win11-dark.css` or `win11-dark.css ad-neon.css` (only applies with `-p`/`-u`; a config file's own `css` field takes precedence with `-c`) |
| `-o`, `--output` | Directory to save the rendered PNG in (defaults to a per-user data directory, see above) |
| `-m`, `--max-results` | Maximum number of results to render (only applies with `-p`/`-u`; default: 3) |
| `-W`, `--width` | Screenshot width in px (overrides any canvas size baked into the selected theme; defaults to 1280) |
| `-H`, `--height` | Screenshot height in px (overrides any canvas size baked into the selected theme; defaults to 720) |

With `-p`, the plugin's `ExecuteFileName` is invoked as a subprocess with a
`{"method": "query", "parameters": [query]}` request and its results become the
rendered rows. `-u` is mutually exclusive with `-p` — the zip is extracted to a
temporary directory (its `plugin.json` is located automatically, even if the zip
wraps everything in a subfolder), then handled exactly like `-p`.

With `-i`, no query is run — instead it renders the plugin-manager mockup you'd see
after typing `pm install <name>`: query box shows `pm install {Name}`, and the single
result is `{Name} by {Author}` / `{Description}`, all read straight from the plugin's
`plugin.json`.

## Edit mode

`flow-render edit -p ./plugin` opens a local browser tab with a live, editable
preview of the mockup — useful for building promo/hero-shot themes (the
`ad-*.css` family) without hand-tuning CSS and re-running screenshots to
check the result.

```bash
flow-render edit -p ./plugin                       # blank starting theme
flow-render edit -p ./plugin -q "install"          # preview against a query
flow-render edit -p ./plugin -s ad-neon.css        # continue editing a theme
flow-render edit -p ./plugin -q "install" -m 5     # show up to 5 results
```

`-m`/`--max-results` works the same as on the normal command. `-o`, `-i`, `-c`,
`-W`, `-H` don't apply to `edit` (canvas size is set live in the editor instead
of `-W`/`-H`).

In the editor:
- Click any element in the preview (the window, icon, a result's title, etc.)
  to select it, then adjust its translate X/Y/Z, rotate X/Y/Z, scale,
  opacity, perspective, and drop shadow (offset X/Y, blur, color, opacity)
  with the sliders — each has a live-editable number box and a reset (↺)
  button, with wide ranges (e.g. translate up to ±2000px, rotate up to
  ±360°, scale up to 5x) to cover everything from subtle nudges to
  dramatic hero-shot compositions. You can also drag an element directly in
  the preview to set translate X/Y, and scroll the mouse wheel over it to
  adjust scale — both stay in sync with the slider panel. Because these are
  shared CSS selectors, editing e.g. "Title" affects every result row, not
  just one. `.icon`, `#GlassIcon`, and `.Hotkey` keep their own built-in
  vertical centering
  underneath whatever you add on top.
- "Perspective" (0 = off) is what actually gives translateZ/rotateX/rotateY
  real 3D depth — without it, Z movement has no visible foreshortening.
  Raise it for a stronger "pop toward the viewer" effect, needed for the
  tilted-window look the `ad-*.css` hero themes use.
- Transforming anything other than the window itself (an icon, a title, etc.)
  lets it visually extend past the window's edges — e.g. a large translateZ
  or scale can make an icon "float" off the window — instead of being
  clipped to the window's bounds.
- "Selected result" picks which row is highlighted, for previewing the
  selected-row styling on any of the plugin's actual results. "Selected row"
  in the Elements list is a separate selectable target (`.selecteditem`) for
  transforming whichever row that is — e.g. scaling it up slightly as
  emphasis — independently of "Result row", which affects every row.
- The canvas (behind the window) is edited globally, not per element: choose
  exactly one of theme default, gradient, or transparent — a transparent
  canvas shows a gray/white checkerboard in the editor so it reads as
  "transparent," not just "dark." A gradient can be linear (with an angle)
  or radial (with a center X/Y position instead of an angle), with 2 to 6
  color stops (each with its own position); "+ Add color stop" and a
  per-stop ✕ button (once past 2 stops) manage
  the list. The canvas's pixel bounds are outlined in the preview. Canvas
  width/height set the actual final screenshot's pixel size (not just the
  live preview, up to 8000px) — saved as a `/* flow-render-canvas: WxH */`
  marker at the top of the theme, which the normal (non-edit) command reads
  automatically when that theme is selected with `-s`. `-W`/`-H` on the
  command line override it.
- "+ Add layer" adds a freeform text layer (up to 4), each a sibling of the
  window rather than nested inside it, so it doesn't inherit the window's
  own rotation — with its own Jinja2 template (e.g. `{{ plugin.Name }}`),
  a choice of font family (several web-safe options, or the theme's
  default), font size, color with its own opacity slider, weight, plus the
  same translate/rotate/scale/opacity/shadow controls as elements. The
  template stays live in the saved CSS: reusing the theme against a
  different plugin later updates the text automatically. "🗑 Remove layer"
  deactivates the currently selected layer, freeing its slot for reuse.
- "Save" writes `src/flow_render/static/<name>.css`, ready to use immediately
  with `-s <name>.css` on the normal (non-edit) command.
- "📷 Capture screenshot" runs the real screenshot pipeline against whatever
  you're currently editing (saved or not) and writes it to the normal
  per-user output directory — no need to save first or leave the editor.

## Config format

See `example/config.json`:

```json
{
    "keyword": "pm",
    "query": "install Steam Search",
    "icon": "data:image/png;base64,...",
    "max_results": 1,
    "selection": 0,
    "css": null,
    "query_suggestion": "",
    "results": [
        {
            "title": "Steam Search by Garulf",
            "subtitle": "Search and launch your Steam Games",
            "icon": "data:image/png;base64,..."
        }
    ]
}
```

- `icon` accepts a data URI or a path relative to the config file — relative paths are
  resolved and inlined automatically.
- `selection` is the index of the highlighted row.
- `query_suggestion` is auto-filled from the selected result's title when left empty.
- `max_results` also caps how many entries from `results` actually get rendered (any
  beyond it are dropped from the screenshot). When `results` has more entries than
  `max_results`, a cosmetic scrollbar thumb is drawn on the results list to suggest more
  results exist below (this tool renders a single static screenshot, so it's a visual cue
  only, not an actually scrollable list).
- `css` names a stylesheet (or a list of stylesheets, e.g. `["win11-dark.css", "ad-neon.css"]`)
  to inline on top of the default `style.css`. Each is applied in order, so later
  entries win the cascade over earlier ones. Each is looked
  up relative to the working directory first, then in the bundled `static/`, where several
  variants ship (`hero.css`, `hero1.css` … `hero4.css`, `style.css`, `win11-light.css`,
  `win11-dark.css` — the last two mimic Flow Launcher's "Windows 11" theme). Templates resolve
  the same way, so a local `base.html` overrides the bundled one.
- For product-page hero shots, `hero-win11-light.css` and `hero-win11-dark.css` render the
  launcher centered on a mock Windows 11 desktop — taskbar, start button, pinned icons, and
  a couple of blank cascaded windows behind it — using the real `win11-light.css`/`win11-dark.css`
  launcher chrome. `hero-win11-accent.css` is the same desktop mockup with a saturated accent
  wallpaper instead, on the default launcher theme.
- Generated Flow Launcher themes live in the bundled `static/themes/` — use them with
  `"css": "themes/dracula.css"` (or `themes/win11light-dark.css`, etc.).
  Regenerate them from the current Flow Launcher release with `make themes`,
  which refreshes the vendored XAML in `themes/xaml/` and rewrites the CSS.
