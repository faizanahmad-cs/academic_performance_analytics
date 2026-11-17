import os
import sys
import subprocess
import time

def start_backend():
    print("[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...")
    cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    return subprocess.Popen(cmd)

def start_frontend():
    port = os.getenv("PORT", "8501")
    print(f"[2/2] Starting Streamlit Presentation Layer on port {port} ...")
    cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true"
    ]
    return subprocess.Popen(cmd)

def main():
    print("=" * 65)
    print("   ACADEMIC PERFORMANCE ANALYTICS SYSTEM")
    print("   Department of Computer Science - Aligarh Muslim University")
    print("   MCA Semester III | Session 2026-27 | CAMS-3P01 Mini Project")
    print("=" * 65)

    backend_proc = start_backend()
    time.sleep(2)  # Give backend a moment to boot
    frontend_proc = start_frontend()

    print("\n✅ System is running!")
    print("👉 Frontend Dashboard : http://localhost:8501")
    print("👉 Backend API Docs   : http://127.0.0.1:8000/docs")
    print("Press Ctrl+C to terminate both servers.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        frontend_proc.terminate()
        backend_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
