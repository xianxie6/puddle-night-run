# 本地预览服务器（禁用缓存）：python3 serve.py  然后打开 http://localhost:8765
# 另支持 POST /save?name=xxx.webm 把录屏保存到 recordings/
import http.server, os, re, urllib.parse
ROOT = os.path.dirname(os.path.abspath(__file__))
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != '/save': self.send_error(404); return
        name = urllib.parse.parse_qs(u.query).get('name', ['rec.webm'])[0]
        name = re.sub(r'[^\w.\-]', '_', os.path.basename(name))
        os.makedirs(os.path.join(ROOT, 'recordings'), exist_ok=True)
        n = int(self.headers.get('Content-Length', 0))
        with open(os.path.join(ROOT, 'recordings', name), 'wb') as f: f.write(self.rfile.read(n))
        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
os.chdir(ROOT)
http.server.ThreadingHTTPServer(('127.0.0.1', 8765), H).serve_forever()
