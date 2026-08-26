import json, threading, uuid, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
JOBS.mkdir(exist_ok=True)

_pending = []
_lock = threading.Lock()
_server = None


def create_job(context, topic):
    global _pending

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    d = JOBS / job_id
    d.mkdir(parents=True, exist_ok=True)

    req = {
        "job_id": job_id,
        "context": context,
        "topic": topic,
        "output_file": "output.json"
    }

    (d / "request.json").write_text(
        json.dumps(req, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    with _lock:
        _pending.append(job_id)

    print(f"[BRIDGE] job created: {job_id} ({topic})")

    return job_id


def get_job(wait_timeout=0):
    """
    Long-poll: nếu chưa có job, chờ tối đa wait_timeout giây rồi mới trả về
    None, thay vì trả về ngay lập tức. Giúp extension nhận job gần như tức
    thì thay vì phụ thuộc vào chu kỳ poll cố định phía client.
    """
    end = time.time() + wait_timeout

    while True:
        with _lock:
            job_id = _pending.pop(0) if _pending else None

        if job_id:
            print(f"[BRIDGE] job dispatched: {job_id}")
            return json.loads(
                (JOBS / job_id / "request.json").read_text(encoding="utf-8")
            )

        if time.time() >= end:
            return None

        time.sleep(0.3)


def wait_for_result(job_id, timeout=600):
    p = JOBS / job_id / "output.json"
    end = time.time() + timeout

    while time.time() < end:
        if p.exists() and p.stat().st_size:
            return p
        time.sleep(0.5)

    return None


class H(BaseHTTPRequestHandler):

    def send(self, code, body, typ="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            print("[BRIDGE] Client đã đóng kết nối trước khi nhận response")

    def do_OPTIONS(self):
        self.send(204, b"")

    def do_GET(self):
        p = urlparse(self.path).path

        if p == "/api/job":
            job = get_job(wait_timeout=25)  # ← chờ ở đây tới 25s
            return self.send(200, json.dumps({"job": job}, ensure_ascii=False))

        if p.startswith("/api/files/"):
            parts = p[len("/api/files/"):].split("/")

            if len(parts) != 2:
                return self.send(404, b"not found", "text/plain")

            f = JOBS / parts[0] / parts[1]

            if not f.is_file():
                return self.send(404, b"not found", "text/plain")

            return self.send(200,f.read_bytes(), "text/plain; charset=utf-8")

        if p == "/api/health":
            return self.send(200, b'{"ok":true}')

        return self.send(404, b"not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/result":
            return self.send(404, b"not found", "text/plain")

        n = int(self.headers.get("Content-Length", "0"))

        try:
            x = json.loads(self.rfile.read(n).decode())
            job_id = x["job_id"]
            data = x["data"]

            d = JOBS / job_id
            d.mkdir(parents=True, exist_ok=True)

            (d / "output.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            print(f"[BRIDGE] result received: {job_id}")

            self.send(200, b'{"ok":true}')

        except Exception as e:
            self.send(
                400,
                json.dumps({"ok": False, "error": str(e)})
            )

    def log_message(self, *a):
        pass


def start_server(host="127.0.0.1", port=8765):
    global _server

    if _server is None:
        _server = ThreadingHTTPServer((host, port), H)
        threading.Thread(
            target=_server.serve_forever,
            daemon=True
        ).start()

    return _server