import http.server
import json
import os
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .config import Config
from .edit_state import EditState, edit_state_to_css, edit_state_to_dict, apply_update
from .image import crop_to_content
from .main import default_output_dir
from .renderer import render
from .screenshot import capture_screenshot

STATIC_DIR = Path(__file__).parent / 'static'
EDITOR_HTML_PATH = Path(__file__).parent / 'edit_static' / 'editor.html'


class EditSession:
    def __init__(self, config: Config, base_css_files: list):
        self.config = config
        self.state = EditState(base_css_files=list(base_css_files))
        self._preview_path = Path.cwd() / f".web-render-edit-preview-{os.getpid()}.css"
        self._last_good_html: str = ""
        self.last_error: Optional[str] = None

    def render_preview(self) -> str:
        self._preview_path.write_text(edit_state_to_css(self.state))
        self.config.css = [self._preview_path.name]
        try:
            html = render(self.config)
        except Exception as exc:
            self.last_error = str(exc)
            return self._last_good_html
        self._last_good_html = html
        self.last_error = None
        return html

    def cleanup(self) -> None:
        if self._preview_path.exists():
            self._preview_path.unlink()

    def state_payload(self) -> dict:
        data = edit_state_to_dict(self.state)
        data['selection'] = self.config.selection
        data['results'] = [
            {'title': result['title'], 'subtitle': result['subtitle']}
            for result in self.config.results
        ]
        return data

    def capture_screenshot(self) -> Path:
        html = self.render_preview()
        output_dir = default_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='web-render-edit-capture-') as build_dir:
            html_path = Path(build_dir) / 'output.html'
            html_path.write_text(html)
            raw_image = capture_screenshot(
                str(html_path), width=self.state.canvas_width, height=self.state.canvas_height)
            unique_suffix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex[:8]}"
            return crop_to_content(raw_image, output_dir / f"output_{unique_suffix}.png")


def make_request_handler(session: EditSession):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str = 'text/html') -> None:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/':
                self._send(200, EDITOR_HTML_PATH.read_bytes())
            elif self.path == '/preview':
                try:
                    body = session.render_preview().encode('utf-8')
                except Exception as exc:
                    self._send(500, json.dumps({'error': str(exc)}).encode('utf-8'), 'application/json')
                    return
                self._send(200, body)
            elif self.path == '/preview-error':
                body = json.dumps({'error': session.last_error}).encode('utf-8')
                self._send(200, body, 'application/json')
            elif self.path == '/state':
                body = json.dumps(session.state_payload()).encode('utf-8')
                self._send(200, body, 'application/json')
            else:
                self._send(404, b'not found')

        def _error(self, status: int, message: str) -> None:
            self._send(status, json.dumps({'error': message}).encode('utf-8'), 'application/json')

        def do_POST(self):
            expected_host = f"{self.server.server_address[0]}:{self.server.server_address[1]}"
            if self.headers.get('Host') != expected_host:
                self._error(403, 'invalid host')
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                payload = json.loads(self.rfile.read(length) or b'{}')
                if self.path == '/update':
                    # `selection` is a Config field (which result row is highlighted),
                    # not part of the EditState theme model, so it's applied directly
                    # rather than through apply_update.
                    if payload.get('type') == 'selection':
                        session.config.selection = int(payload['index'])
                    else:
                        apply_update(session.state, payload)
                    self._send(204, b'')
                elif self.path == '/capture':
                    final_image = session.capture_screenshot()
                    self._send(200, json.dumps({'path': str(final_image)}).encode('utf-8'), 'application/json')
                elif self.path == '/save':
                    raw_filename = str(payload.get('filename', '') or '').strip()
                    filename = Path(raw_filename).stem
                    if not filename or filename == '..':
                        self._error(400, 'filename is required')
                        return
                    target = STATIC_DIR / f"{filename}.css"
                    target.write_text(edit_state_to_css(session.state))
                    self._send(200, json.dumps({'path': str(target)}).encode('utf-8'), 'application/json')
                else:
                    self._send(404, b'not found')
            except Exception as exc:
                self._error(400, str(exc))

        def log_message(self, format, *args):
            pass

    return Handler


def build_server(config: Config, base_css_files: list, host: str = '127.0.0.1', port: int = 0):
    session = EditSession(config, base_css_files)
    server = http.server.ThreadingHTTPServer((host, port), make_request_handler(session))
    server.session = session
    return server


def run(config: Config, base_css_files: list, host: str = '127.0.0.1', port: int = 0) -> None:
    server = build_server(config, base_css_files, host=host, port=port)
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(f"Edit mode running at {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.session.cleanup()
        server.server_close()
