"""
server.py  --  tiny web server (Python standard library only, no pip install)
Run:  python server.py [port]      then open  http://127.0.0.1:8000
"""
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from regex_parser import RegexSyntaxError
from dfa_converter import AutomatonTooLarge
import engine

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "static", "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        else:
            self._send(404, json.dumps({"ok": False, "error": "Not found"}))

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(size) or b"{}")
            regex = str(body.get("regex", ""))
            if self.path == "/api/analyze":
                tests = [str(t) for t in body.get("tests", [])]
                out = engine.analyze(regex, tests, str(body.get("method", "hopcroft")))
            elif self.path == "/api/generate":
                out = {"regex": regex,
                       "strings": engine.generate(regex, body.get("count", 10), body.get("max_len", 12))}
            else:
                return self._send(404, json.dumps({"ok": False, "error": "Not found"}))
            out["ok"] = True
            self._send(200, json.dumps(out))
        except RegexSyntaxError as e:
            self._send(200, json.dumps({"ok": False, "error": e.message, "pos": e.pos}))
        except (AutomatonTooLarge, ValueError) as e:
            self._send(200, json.dumps({"ok": False, "error": str(e)}))
        except Exception as e:  # keep the server alive whatever happens
            self._send(500, json.dumps({"ok": False, "error": f"Internal error: {e}"}))

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Regex Testing Platform running at {url}  (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
