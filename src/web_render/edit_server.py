import http.server
import json
import os
import webbrowser
from pathlib import Path

from .config import Config
from .edit_state import EditState, edit_state_to_css, edit_state_to_dict, apply_update
from .renderer import render

STATIC_DIR = Path(__file__).parent / 'static'
EDITOR_HTML_PATH = Path(__file__).parent / 'edit_static' / 'editor.html'


class EditSession:
    def __init__(self, config: Config, base_css_files: list):
        self.config = config
        self.state = EditState(base_css_files=list(base_css_files))
        self._preview_path = Path.cwd() / f".web-render-edit-preview-{os.getpid()}.css"

    def render_preview(self) -> str:
        self._preview_path.write_text(edit_state_to_css(self.state))
        self.config.css = [*self.state.base_css_files, self._preview_path.name]
        return render(self.config)

    def cleanup(self) -> None:
        if self._preview_path.exists():
            self._preview_path.unlink()


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
                self._send(200, session.render_preview().encode('utf-8'))
            elif self.path == '/state':
                body = json.dumps(edit_state_to_dict(session.state)).encode('utf-8')
                self._send(200, body, 'application/json')
            else:
                self._send(404, b'not found')

        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length) or b'{}')
            if self.path == '/update':
                apply_update(session.state, payload)
                self._send(204, b'')
            elif self.path == '/save':
                filename = Path(payload['filename']).stem
                target = STATIC_DIR / f"{filename}.css"
                target.write_text(edit_state_to_css(session.state))
                self._send(200, json.dumps({'path': str(target)}).encode('utf-8'), 'application/json')
            else:
                self._send(404, b'not found')

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
