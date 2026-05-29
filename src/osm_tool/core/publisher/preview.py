"""切片预览服务器"""
import http.server
import threading
import webbrowser
from pathlib import Path


PREVIEW_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>OSM Tool - 切片预览</title>
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const params = new URLSearchParams(window.location.search);
        const tilesUrl = params.get('tiles') || '/tiles/{z}/{x}/{y}.pbf';
        const bounds = JSON.parse(params.get('bounds') || '[73, 3, 136, 54]');
        const minzoom = parseInt(params.get('minzoom') || '0');
        const maxzoom = parseInt(params.get('maxzoom') || '14');

        const map = new maplibregl.Map({
            container: 'map',
            style: {
                version: 8,
                sources: {
                    tiles: {
                        type: 'vector',
                        tiles: [tilesUrl],
                        minzoom: minzoom,
                        maxzoom: maxzoom,
                        bounds: bounds
                    }
                },
                layers: []
            },
            center: [(bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2],
            zoom: 6
        });
        map.addControl(new maplibregl.NavigationControl());
    </script>
</body>
</html>
"""


class TilePreviewServer:
    """本地切片预览 HTTP 服务器"""

    def __init__(self, tiles_dir: str, port: int = 8765):
        self._tiles_dir = Path(tiles_dir)
        self._port = port
        self._server = None
        self._thread = None

    def start(self) -> str:
        """启动预览服务，返回预览 URL"""
        handler = self._make_handler(self._tiles_dir)
        self._server = http.server.HTTPServer(("localhost", self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        url = f"http://localhost:{self._port}/preview.html?tiles=/{{z}}/{{x}}/{{y}}.pbf"
        webbrowser.open(url)
        return url

    def stop(self) -> None:
        """停止预览服务"""
        if self._server:
            self._server.shutdown()

    @staticmethod
    def _make_handler(tiles_dir: Path):
        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/preview.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(PREVIEW_HTML.encode("utf-8"))
                elif self.path.startswith("/tiles/"):
                    # 解析 /tiles/{z}/{x}/{y}.pbf
                    parts = self.path.replace("/tiles/", "").split("/")
                    if len(parts) == 3:
                        z, x, y_file = parts
                        tile_path = tiles_dir / z / x / y_file
                        if tile_path.exists():
                            self.send_response(200)
                            self.send_header("Content-Type", "application/x-protobuf")
                            self.end_headers()
                            self.wfile.write(tile_path.read_bytes())
                            return
                    self.send_error(404)
                else:
                    super().do_GET()

            def log_message(self, format, *args):
                pass  # 静默日志

        return Handler
