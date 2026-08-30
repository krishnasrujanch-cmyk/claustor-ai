"""
Claustor Worker — Celery + HTTP health server for Cloud Run
"""
import os
import sys
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"healthy","service":"claustor-worker"}')
    def log_message(self, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server listening on port {port}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    # Health server in background thread
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    print("Health server started", flush=True)

    # Beat in subprocess
    beat_proc = subprocess.Popen([
        sys.executable, "-m", "celery",
        "-A", "app.workers.celery_app", "beat",
        "--loglevel=info",
        "--scheduler", "celery.beat:PersistentScheduler",
    ], stdout=sys.stdout, stderr=sys.stderr)
    print("Celery beat started", flush=True)

    # Worker in foreground — use os.execvp to replace this process
    # This ensures all signals are handled properly
    print("Starting Celery worker...", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

    worker_proc = subprocess.Popen([
        sys.executable, "-m", "celery",
        "-A", "app.workers.celery_app", "worker",
        "--loglevel=info",
        "-Q", "enterprise_queue,pro_queue,starter_queue,free_queue",
        "--concurrency=1",
        "--pool=threads",
        "--without-heartbeat",
        "--without-mingle",
    ], stdout=sys.stdout, stderr=sys.stderr)

    # Wait for worker
    rc = worker_proc.wait()
    beat_proc.terminate()
    sys.exit(rc)
