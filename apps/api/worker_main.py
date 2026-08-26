"""
Claustor Worker — Celery + HTTP health server for Cloud Run
"""
import os
import threading
import subprocess
import sys
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
    # Start health server in background thread
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    # Start Celery worker
    worker_proc = subprocess.Popen([
        "celery", "-A", "app.workers.celery_app", "worker",
        "--loglevel=info",
        "-Q", "enterprise_queue,pro_queue,starter_queue,free_queue",
        "--concurrency=1",
        "--pool=threads",  # No fork = no OOM. bge-m3 runs in subprocess anyway
    ])
    print("Celery worker started", flush=True)

    # Start Celery Beat scheduler (daily alerts, monthly resets)
    beat_proc = subprocess.Popen([
        "celery", "-A", "app.workers.celery_app", "beat",
        "--loglevel=info",
        "--scheduler", "celery.beat:PersistentScheduler",
    ])
    print("Celery beat started", flush=True)

    # Wait for worker (primary process)
    worker_proc.wait()
    beat_proc.terminate()
    sys.exit(worker_proc.returncode)
