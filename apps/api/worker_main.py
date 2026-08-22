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

    # Start Celery worker as subprocess (keeps health thread alive)
    proc = subprocess.Popen([
        "celery", "-A", "app.workers.celery_app", "worker",
        "--loglevel=info",
        "-Q", "enterprise_queue,pro_queue,starter_queue,free_queue",
        "--concurrency=2",
    ])
    
    print("Celery worker started", flush=True)
    proc.wait()
    sys.exit(proc.returncode)
