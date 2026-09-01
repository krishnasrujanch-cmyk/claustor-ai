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

    # Keep Neon compute warm — ping every 3 min to prevent scale-to-zero
    def _keep_db_warm():
        import time
        import asyncio as _aio
        from sqlalchemy.ext.asyncio import create_async_engine as _cae
        from sqlalchemy import text as _text
        import os, ssl as _ssl
        db_url = os.environ.get("DATABASE_URL", "")
        # Use direct endpoint (strip -pooler)
        db_url = db_url.replace("-pooler.", ".")
        while True:
            time.sleep(180)  # 3 minutes
            try:
                async def _ping():
                    ctx = _ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = _ssl.CERT_NONE
                    engine = _cae(db_url, connect_args={"ssl": ctx, "statement_cache_size": 0})
                    async with engine.connect() as conn:
                        await conn.execute(_text("SELECT 1"))
                    await engine.dispose()
                _aio.run(_ping())
            except Exception as e:
                print(f"DB warm ping failed: {e}", flush=True)

    db_warm_thread = threading.Thread(target=_keep_db_warm, daemon=True)
    db_warm_thread.start()
    print("DB warm-ping thread started (every 3 min)", flush=True)

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
