"""
Claustor Worker — Celery worker + Beat + HTTP health server for Cloud Run
Runs Celery directly in-process with health server in background thread.
"""
import os
import sys
import threading
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

    # Start Beat in background thread
    import subprocess
    beat_proc = subprocess.Popen([
        "celery", "-A", "app.workers.celery_app", "beat",
        "--loglevel=info",
        "--scheduler", "celery.beat:PersistentScheduler",
    ], stdout=sys.stdout, stderr=sys.stderr, bufsize=1)
    print("Celery beat started", flush=True)

    # Run Celery worker directly in main process (no subprocess)
    # This ensures logs stream properly and no silent crashes
    print("Starting Celery worker...", flush=True)
    from app.workers.celery_app import app
    app.worker_main([
        "worker",
        "--loglevel=info",
        "-Q", "enterprise_queue,pro_queue,starter_queue,free_queue",
        "--concurrency=1",
        "--pool=threads",
    ])
