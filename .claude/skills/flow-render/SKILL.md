---
name: flow-render
description: Generate Flow Launcher search-result screenshots (transparent PNGs) with the flow-render CLI — from a config JSON, a local plugin directory, a plugin .zip/URL, or the "pm install" plugin-manager view, in any bundled theme. Use when asked to render, screenshot, or mock up a Flow Launcher plugin for a README, store listing, or hero/promo image, or to pick/try a flow-render theme.
---

# flow-render

`flow-render` renders a Flow Launcher search-window mockup to HTML, screenshots it in
headless Chromium, crops it to content, and writes `output_<timestamp>_<id>.png`. It
prints `Saved <path>` for each file it writes — use that path, don't guess it.

## 1. Pick the invocation

Inside this repo, run it via `uv run flow-render …` (or `make run …`, which also
bootstraps `.venv` and Chromium). Elsewhere, use `flow-render` if installed
(`uv tool install <repo>` + `playwright install chromium`).

| Goal | Command |
| --- | --- |
| Run a real plugin against a query | `flow-render -p ./path/to/plugin -q "query"` |
| Plugin from a release zip or URL | `flow-render -u https://…/plugin.zip -q "query"` |
| "pm install <Name>" store-style shot | `flow-render -p ./plugin -i` (or `-u … -i`) |
| Idle search window (placeholder + clock, no plugin) | `flow-render --empty -s win11-dark --clock "02:42 PM"` |
| Hand-authored / reproducible mockup | `flow-render -c ./config.json` |
| Interactively design a promo theme | `flow-render edit -p ./plugin [-q "query"] [-s theme]` (opens a browser; needs a human) |

Common flags:
- `-o DIR`: where to save the PNG. **Always pass `-o`** when the image is meant for a
  repo (e.g. `-o ./docs/images`); the default is a per-user data dir
  (`~/.local/share/flow-render/output`, `%LOCALAPPDATA%\flow-render\output`, …).
- `-s THEME [THEME …]`: stylesheets, `.css` optional, later ones win. Only applies
  with `-p`/`-u`/`--empty`; with `-c` the config's own `css` field is used.
- `--clock "HH:MM AM"`: time shown by `--empty`. Pass it for reproducible images;
  otherwise the current time is baked in.
- `-m N`: rows shown (default 3). If the plugin returns more results, a scrollbar thumb
  is drawn to show there are more rows.
- `-W`/`-H`: canvas size in px (default 1280×720 unless the theme embeds one).
- `--hide-caret`: drop the text cursor (cleaner for docs). Not with `-c`; see below.
- `--save-json`: also write the resolved config next to the PNG. Do this when the user
  may want to tweak titles/icons by hand and re-render with `-c`.
- `--print-json`: dump the resolved config to stdout.

`-p` accepts a directory **or a plugin name**: it looks for a matching folder in the cwd,
then (Windows) in `%APPDATA%\FlowLauncher\Plugins`, matching `Name` or a unique
`Name-<version>`.

## 2. Pick a theme

- Plain launcher look: no `-s` (default), `win11-dark`, `win11-light`.
- Real Flow Launcher themes: `themes/<name>`, e.g. `themes/dracula`, `themes/nord-darker`,
  `themes/win11light-dark`. List them with `ls src/flow_render/static/themes/`; preview
  images are in `example/themes/`.
- Hero/product-page shots on a mock Windows 11 desktop: `hero-win11-dark`,
  `hero-win11-light`, `hero-win11-accent` (also `hero`, `hero1`…`hero4`).
- Custom CSS: any path relative to the cwd. It's resolved before the bundled `static/`
  files, so a local file with the same name overrides the bundled one. Edit-mode
  themes put a `/* flow-render-canvas: WxH */` marker in the CSS, and that sets the
  canvas size.

If the user hasn't specified a theme, use `win11-dark` and tell them which one you used.

## 3. Config JSON (for `-c`)

The easiest way to get a valid config is to start from a real run with `--save-json`,
then edit it. Shape (see `example/config.json`):

```json
{
  "keyword": "st",
  "query": "portal",
  "icon": "./icon.png",
  "max_results": 3,
  "selection": 0,
  "css": ["win11-dark.css"],
  "query_suggestion": "",
  "results": [
    {"title": "Portal 2", "subtitle": "Launch game", "icon": "./icons/portal2.png"}
  ]
}
```

- `icon` fields accept data URIs, URLs, or paths **relative to the config file**. They
  get inlined at render time.
- `selection` is the index of the highlighted row.
- `query_suggestion` left empty is auto-filled with ghost-text autocomplete, but only
  when `query` is a case-insensitive prefix of the selected result's title.
- `css` can be a string or a list. Set `"show_caret": false` to hide the cursor.
- With `-c`, only `-o`, `-W`/`-H`, `--print-json`, and `--save-json` still apply;
  `-s`, `-m`, `-q`, and `--hide-caret` are ignored (set them in the JSON instead).

## 4. Verify

After it prints `Saved …/output_*.png`, open that PNG with the Read tool and check:
the right query text, the expected rows and icons (a broken icon means the path didn't
resolve), the highlighted row, and the theme. Show the user the image path. If the
result has to live somewhere specific, rename or move the file. The tool always writes
a new timestamped name and never overwrites.

## Troubleshooting

- **`BrowserType.launch` fails / `error while loading shared libraries: libatk…`**:
  Chromium's system libraries are missing. Run `uv run playwright install-deps chromium`
  (needs sudo), or `make run … ` which tries that automatically.
  **`Executable doesn't exist`**: run `uv run playwright install chromium`.
- **`Plugin process exited with code …` / `did not return valid JSON`**: `-p` runs the
  plugin's `ExecuteFileName` with flow-render's own Python
  (`python main.py '{"method":"query","parameters":[q]}'`). The plugin's dependencies
  must be importable: usually its vendored `lib/` dir, or install them into the venv.
  Plugins that print anything other than JSON to stdout will break this. Only Python
  plugins are supported (v1 JSON-RPC and `python_v2`). For anything else, write a
  config JSON by hand.
- **Windows-only icons** (`.exe`/`.dll` icon locations like `shell32.dll,220`) only
  resolve on Windows with pywin32; elsewhere they stay unresolved. Replace them with
  image files in a config.
- **Plugin name not found with `-p Name`**: pass the directory path instead; the name
  lookup is exact (or a unique `Name-<version>` prefix).
