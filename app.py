#!/usr/bin/env python3
"""
================================================================================
MAIN APPLICATION ENTRYPOINT
Explainable AI Satellite Telemetry Fault Diagnosis System
================================================================================

This is the CENTRAL ORCHESTRATOR for the entire system.
Responsibilities:
  1. Start the FastAPI backend (port 8000)
  2. Start the Next.js frontend (port 3000)
  3. Initialize all ML modules (FCNN, KG, LLM+RAG)
  4. Manage application lifecycle
  5. Handle system health checks
  6. Provide unified logging

Usage:
  python app.py              # Start everything
  python app.py --backend    # Start only backend
  python app.py --frontend   # Start only frontend
  python app.py --help       # Show all options
================================================================================
"""

import os
import sys
import subprocess
import argparse
import time
import platform
import signal
import socket
from pathlib import Path
from typing import Optional, List
import logging
from urllib import request, error

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.absolute()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

BACKEND_PORT = 8000
FRONTEND_PORT = 3000
DEV_DATABASE_URL = f"sqlite:///{(PROJECT_ROOT / 'backend' / 'dev.db').as_posix()}"

# ============================================================================
# SYSTEM DETECTION
# ============================================================================

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Ensure logs directory exists
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "app.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Fix Windows terminal encoding for emojis
if IS_WINDOWS:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# SUBPROCESS MANAGEMENT
# ============================================================================

class ProcessManager:
    """Manages backend and frontend subprocesses with graceful shutdown."""
    
    def __init__(self):
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.processes: List[subprocess.Popen] = []
        self.backend_port: int = BACKEND_PORT
        self.frontend_port: int = FRONTEND_PORT
        self.backend_python: str = self.resolve_backend_python()
        self.use_dev_database: bool = False

    def check_docker_available(self) -> bool:
        """Check whether the Docker CLI and engine are available."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def check_postgres_port_open(self, host: str = "127.0.0.1", port: int = 5432) -> bool:
        """Check whether PostgreSQL is reachable on the default port."""
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            return False

    def print_database_setup_guide(self) -> None:
        """Print the exact setup steps for Docker/PostgreSQL or SQLite development."""
        logger.info("=" * 80)
        logger.info("[SETUP] DATABASE STATUS")
        logger.info("=" * 80)

        if self.check_docker_available():
            logger.info("[OK] Docker engine is available")
        else:
            logger.warning("[WARN] Docker engine is not available in this session")
            logger.warning("       Start Docker Desktop first, then rerun the command below.")

        if self.check_postgres_port_open():
            logger.info("[OK] PostgreSQL is reachable on 127.0.0.1:5432")
            logger.info("[INFO] Production database path can be used")
        else:
            logger.warning("[WARN] PostgreSQL is not reachable on 127.0.0.1:5432")
            logger.warning("       The app will use the local SQLite development database instead.")
            logger.warning(f"       SQLite DB: {PROJECT_ROOT / 'backend' / 'dev.db'}")

        logger.info("\n[STEPS TO GET POSTGRESQL WORKING ON WINDOWS]")
        logger.info("  1. Install Docker Desktop if it is not installed.")
        logger.info("  2. Start Docker Desktop and wait until the whale icon says it is running.")
        logger.info("  3. Verify the engine with: docker info")
        logger.info("  4. Start PostgreSQL with: docker compose up -d postgres")
        logger.info("  5. Initialize tables with: python backend/scripts/init_db.py")
        logger.info("  6. Create the first admin with: python backend/scripts/create_admin.py")
        logger.info("\n[STEPS TO GET WORKING IMMEDIATELY WITHOUT DOCKER]")
        logger.info("  1. Run: python backend/scripts/setup_dev_db.py")
        logger.info("  2. Start the app normally: python app.py")
        logger.info("  3. Login with admin / Admin@123456")
        logger.info("=" * 80)

    def resolve_backend_python(self) -> str:
        """Prefer backend virtualenv interpreter when available."""
        candidates = [
            BACKEND_DIR / "venv" / "Scripts" / "python.exe",
            BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return sys.executable

    def check_ollama_available(self, timeout: int = 2) -> bool:
        """Check if Ollama server is reachable on localhost:11434."""
        try:
            with request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout) as resp:
                return 200 <= resp.status < 300
        except (error.URLError, TimeoutError, OSError):
            return False

    def run_preflight_checks(self) -> bool:
        """Run lightweight environment checks for backend/frontend startup readiness."""
        logger.info("=" * 80)
        logger.info("[CHECK] PREFLIGHT VALIDATION")
        logger.info("=" * 80)

        ok = True

        checks = [
            (PROJECT_ROOT.exists(), f"Project root exists: {PROJECT_ROOT}"),
            (BACKEND_DIR.exists(), f"Backend directory exists: {BACKEND_DIR}"),
            (FRONTEND_DIR.exists(), f"Frontend directory exists: {FRONTEND_DIR}"),
            ((BACKEND_DIR / "src" / "api" / "main.py").exists(), "Backend entrypoint exists: backend/src/api/main.py"),
            ((FRONTEND_DIR / "package.json").exists(), "Frontend package.json exists"),
        ]

        for passed, message in checks:
            if passed:
                logger.info(f"[OK] {message}")
            else:
                logger.error(f"[FAIL] {message}")
                ok = False

        if Path(self.backend_python).exists():
            logger.info(f"[OK] Backend Python interpreter: {self.backend_python}")
        else:
            logger.warning(f"[WARN] Backend Python interpreter not found on disk, using current: {self.backend_python}")

        if self.check_ollama_available():
            logger.info("[OK] Ollama reachable at http://127.0.0.1:11434")
        else:
            logger.warning("[WARN] Ollama not reachable at http://127.0.0.1:11434")
            logger.warning("       LLM explanations may fall back to deterministic mode.")

        if self.check_docker_available():
            logger.info("[OK] Docker engine is available")
        else:
            logger.warning("[WARN] Docker engine is not available")
            logger.warning("       PostgreSQL containers cannot start until Docker Desktop is running.")

        if self.check_postgres_port_open():
            logger.info("[OK] PostgreSQL is reachable on 127.0.0.1:5432")
            self.use_dev_database = False
        else:
            logger.warning("[WARN] PostgreSQL is not reachable on 127.0.0.1:5432")
            logger.warning("       The backend will use SQLite dev.db for this session.")
            self.use_dev_database = True

        logger.info("=" * 80)
        return ok
    
    def signal_handler(self, signum, frame):
        """Handle CTRL+C gracefully - stop all processes."""
        logger.info("\n🛑 Shutdown signal received. Stopping services...")
        self.stop_all()
        sys.exit(0)
    
    def register_signal_handlers(self):
        """Register CTRL+C handler."""
        signal.signal(signal.SIGINT, self.signal_handler)
        if not IS_WINDOWS:
            signal.signal(signal.SIGTERM, self.signal_handler)
    
    def check_port_available(self, port: int) -> bool:
        """Check if port is available (simple check)."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0  # 0 means port is in use

    def find_available_port(self, preferred_port: int, max_tries: int = 20) -> Optional[int]:
        """Find first available port starting from preferred_port."""
        for port in range(preferred_port, preferred_port + max_tries):
            if self.check_port_available(port):
                return port
        return None

    def get_pids_on_port(self, port: int) -> List[int]:
        """Get process IDs listening on the given port."""
        try:
            if IS_WINDOWS:
                cmd = f'netstat -ano -p tcp | findstr ":{port}"'
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                pids: List[int] = []
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 5 and parts[3].upper() == 'LISTENING':
                        try:
                            pid = int(parts[-1])
                            if pid not in pids and pid != os.getpid():
                                pids.append(pid)
                        except ValueError:
                            continue
                return pids

            cmd = f"lsof -ti :{port}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            pids = []
            for line in result.stdout.splitlines():
                try:
                    pid = int(line.strip())
                    if pid != os.getpid():
                        pids.append(pid)
                except ValueError:
                    continue
            return pids
        except Exception:
            return []

    def free_port(self, port: int) -> bool:
        """Attempt to free a port by terminating listener processes."""
        for _ in range(3):
            pids = self.get_pids_on_port(port)
            if not pids:
                return self.check_port_available(port)

            logger.warning(f"[WARN] Port {port} in use by PID(s): {pids}")
            for pid in pids:
                try:
                    if IS_WINDOWS:
                        kill_result = subprocess.run(
                            ["taskkill", "/PID", str(pid), "/T", "/F"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if kill_result.returncode != 0:
                            subprocess.run(
                                [
                                    "powershell",
                                    "-NoProfile",
                                    "-Command",
                                    f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"
                                ],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                    else:
                        os.kill(pid, signal.SIGTERM)
                except Exception as e:
                    logger.warning(f"[WARN] Could not stop PID {pid}: {e}")

            time.sleep(1)

        return self.check_port_available(port)
    
    def start_backend(self, skip_model_load: bool = False) -> bool:
        """Start FastAPI backend server."""
        logger.info("=" * 80)
        logger.info("[START] BACKEND (FastAPI)")
        logger.info("=" * 80)
        
        self.backend_port = BACKEND_PORT
        if not self.check_port_available(self.backend_port):
            logger.warning(f"[WARN] Backend port {self.backend_port} is already in use. Attempting cleanup...")
            if not self.free_port(self.backend_port):
                fallback_port = self.find_available_port(self.backend_port + 1)
                if fallback_port is None:
                    logger.error(f"[ERROR] No available backend port found after {self.backend_port}")
                    return False
                self.backend_port = fallback_port
                logger.warning(f"[WARN] Using fallback backend port: {self.backend_port}")
            else:
                logger.info(f"[OK] Port {self.backend_port} released")
        
        try:
            # Verify backend directory exists
            if not BACKEND_DIR.exists():
                logger.error(f"[ERROR] Backend directory not found: {BACKEND_DIR}")
                return False
            
            # Verify src directory exists
            backend_src = BACKEND_DIR / 'src'
            if not backend_src.exists():
                logger.error(f"[ERROR] Backend src directory not found: {backend_src}")
                return False
            
            # Set environment variables
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # Real-time output
            env['PYTHONPATH'] = str(BACKEND_DIR)  # Add backend to Python path

            if self.use_dev_database:
                dev_db_path = BACKEND_DIR / 'dev.db'
                env['ENVIRONMENT'] = 'development'
                env['DATABASE_URL'] = f"sqlite:///{dev_db_path.as_posix()}"
                logger.warning(f"[WARN] Using SQLite development database: {dev_db_path}")
                if not dev_db_path.exists():
                    setup_db_script = BACKEND_DIR / 'scripts' / 'setup_dev_db.py'
                    if setup_db_script.exists():
                        logger.info("[SETUP] Creating local dev database before backend start...")
                        setup_result = subprocess.run(
                            [self.backend_python, str(setup_db_script)],
                            cwd=BACKEND_DIR,
                            env=env,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        if setup_result.returncode != 0:
                            logger.error(f"[ERROR] Dev database setup failed: {setup_result.stderr}")
                            return False
                        logger.info("[OK] Local dev database created")
            
            # Build command - import path must be relative to PYTHONPATH
            cmd = [
                self.backend_python,
                "-m",
                "uvicorn",
                "src.api.main:app",  # Import from src.api.main
                "--host", "127.0.0.1",
                "--port", str(self.backend_port),
                "--reload",  # Auto-reload on code changes
            ]
            
            logger.info(f"[CMD] {' '.join(cmd)}")
            logger.info(f"[DIR] Working directory: {BACKEND_DIR}")
            logger.info(f"[URL] Running at: http://127.0.0.1:{self.backend_port}")
            logger.info(f"[DOC] API Docs at: http://127.0.0.1:{self.backend_port}/docs")
            
            # Start process
            self.backend_process = subprocess.Popen(
                cmd,
                cwd=BACKEND_DIR,  # Run from backend/ directory
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append(self.backend_process)
            
            # Give backend time to start
            time.sleep(3)
            
            if self.backend_process.poll() is None:
                logger.info("[OK] Backend started successfully!")
                return True
            else:
                logger.error("[FAIL] Backend failed to start")
                stdout, stderr = self.backend_process.communicate(timeout=1)
                logger.error(f"Error: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to start backend: {e}")
            return False
    
    def start_frontend(self) -> bool:
        """Start Next.js frontend development server."""
        logger.info("=" * 80)
        logger.info("[START] FRONTEND (Next.js)")
        logger.info("=" * 80)
        
        self.frontend_port = FRONTEND_PORT
        if not self.check_port_available(self.frontend_port):
            logger.warning(f"[WARN] Frontend port {self.frontend_port} is already in use. Attempting cleanup...")
            if not self.free_port(self.frontend_port):
                fallback_port = self.find_available_port(self.frontend_port + 1)
                if fallback_port is None:
                    logger.error(f"[ERROR] No available frontend port found after {self.frontend_port}")
                    return False
                self.frontend_port = fallback_port
                logger.warning(f"[WARN] Using fallback frontend port: {self.frontend_port}")
            else:
                logger.info(f"[OK] Port {self.frontend_port} released")
        
        try:
            # Verify frontend directory exists
            if not FRONTEND_DIR.exists():
                logger.error(f"[ERROR] Frontend directory not found: {FRONTEND_DIR}")
                return False
            
            # Check if node_modules exists
            node_modules = FRONTEND_DIR / "node_modules"
            package_json = FRONTEND_DIR / "package.json"
            
            if not package_json.exists():
                logger.error(f"[ERROR] package.json not found in {FRONTEND_DIR}")
                return False
            
            if not node_modules.exists():
                logger.info("[INSTALL] Installing frontend dependencies (npm install)...")
                install_cmd = ["npm", "install"]
                
                # On Windows, use shell=True for npm commands
                shell = IS_WINDOWS
                
                result = subprocess.run(
                    install_cmd,
                    cwd=FRONTEND_DIR,
                    capture_output=True,
                    text=True,
                    timeout=300,  # Increase timeout to 5 minutes
                    shell=shell
                )
                if result.returncode != 0:
                    logger.error(f"[ERROR] npm install failed: {result.stderr}")
                    return False
                logger.info("[OK] Dependencies installed")
            
            # Build command
            cmd = ["npm", "run", "dev"]
            
            logger.info(f"[CMD] {' '.join(cmd)}")
            logger.info(f"[DIR] Working directory: {FRONTEND_DIR}")
            logger.info(f"[URL] Running at: http://localhost:{self.frontend_port}")
            
            # Set environment
            env = os.environ.copy()
            env['PORT'] = str(self.frontend_port)
            env['NEXT_PUBLIC_API_URL'] = f"http://127.0.0.1:{self.backend_port}"
            
            # On Windows, npm commands need shell=True for proper execution
            # But for subprocess.Popen with streaming output, we handle it differently
            if IS_WINDOWS:
                # On Windows, explicitly call cmd.exe to handle npm
                cmd = ["cmd", "/c", "npm", "run", "dev"]
            
            # Start process
            self.frontend_process = subprocess.Popen(
                cmd,
                cwd=FRONTEND_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append(self.frontend_process)
            
            # Give frontend time to start
            time.sleep(5)
            
            if self.frontend_process.poll() is None:
                logger.info("[OK] Frontend started successfully!")
                return True
            else:
                logger.error("[FAIL] Frontend failed to start")
                stdout, stderr = self.frontend_process.communicate(timeout=1)
                logger.error(f"Error: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to start frontend: {e}")
            return False
    
    def stop_all(self):
        """Stop all running processes gracefully."""
        logger.info("\n[STOP] Stopping all services...")
        
        for proc in self.processes:
            if proc.poll() is None:  # Process still running
                try:
                    if IS_WINDOWS:
                        proc.terminate()
                    else:
                        proc.send_signal(signal.SIGTERM)
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                except Exception as e:
                    logger.error(f"Error stopping process: {e}")
        
        logger.info("[OK] All services stopped")
    
    def monitor_processes(self):
        """Monitor running processes and log output (streaming)."""
        import select
        import threading
        
        def log_output(proc, name):
            """Log subprocess output in real-time."""
            for line in iter(proc.stdout.readline, ''):
                if line:
                    logger.info(f"[{name}] {line.rstrip()}")
        
        def log_errors(proc, name):
            """Log subprocess errors in real-time."""
            for line in iter(proc.stderr.readline, ''):
                if line:
                    logger.warning(f"[{name}] {line.rstrip()}")
        
        # Start logging threads
        if self.backend_process:
            threading.Thread(target=log_output, args=(self.backend_process, "BACKEND"), daemon=True).start()
            threading.Thread(target=log_errors, args=(self.backend_process, "BACKEND"), daemon=True).start()
        
        if self.frontend_process:
            threading.Thread(target=log_output, args=(self.frontend_process, "FRONTEND"), daemon=True).start()
            threading.Thread(target=log_errors, args=(self.frontend_process, "FRONTEND"), daemon=True).start()
        
        # Keep alive and monitor
        try:
            while True:
                time.sleep(1)
                
                # Check if processes are still alive
                if self.backend_process and self.backend_process.poll() is not None:
                    logger.error("[WARN] Backend process died!")
                
                if self.frontend_process and self.frontend_process.poll() is not None:
                    logger.error("[WARN] Frontend process died!")
                
        except KeyboardInterrupt:
            pass
    
    def run_all(self):
        """Start both backend and frontend."""
        logger.info("\n" + "=" * 80)
        logger.info("[INIT] INITIALIZING COMPLETE SYSTEM")
        logger.info("=" * 80 + "\n")
        
        # Register signal handlers for graceful shutdown
        self.register_signal_handlers()

        # Print database setup guidance so the user knows exactly what to do
        self.print_database_setup_guide()
        
        # Start backend
        if not self.start_backend():
            logger.error("[ERROR] Failed to start backend. Aborting.")
            return False
        
        time.sleep(2)
        
        # Start frontend
        if not self.start_frontend():
            logger.error("[ERROR] Failed to start frontend. Backend is still running.")
            logger.error("        Stopping backend...")
            self.stop_backend()
            return False
        
        # Display summary
        logger.info("\n" + "=" * 80)
        logger.info("[OK] SYSTEM INITIALIZED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info("\n[SERVICES] RUNNING:")
        logger.info(f"   * Backend  -> http://127.0.0.1:{self.backend_port}")
        logger.info(f"   * Frontend -> http://localhost:{self.frontend_port}")
        logger.info(f"   * API Docs -> http://127.0.0.1:{self.backend_port}/docs")
        logger.info("\n" + "=" * 80)
        logger.info("[BROWSER] OPEN THIS URL:")
        logger.info(f"          >>> http://localhost:{self.frontend_port} <<<")
        logger.info("=" * 80)
        logger.info("\n[CTRL] To stop all services, press CTRL+C")
        logger.info("=" * 80 + "\n")
        
        # Monitor processes
        self.monitor_processes()
    
    def stop_backend(self):
        """Stop only backend."""
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
            logger.info("[OK] Backend stopped")
    
    def stop_frontend(self):
        """Stop only frontend."""
        if self.frontend_process:
            self.frontend_process.terminate()
            self.frontend_process.wait()
            logger.info("[OK] Frontend stopped")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main orchestrator function."""
    parser = argparse.ArgumentParser(
        description="Explainable AI Satellite Telemetry - Main Entrypoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                # Start backend + frontend
  python app.py --backend      # Start only backend
  python app.py --frontend     # Start only frontend
  python app.py --version      # Show version info
        """
    )
    
    parser.add_argument(
        '--backend',
        action='store_true',
        help='Start only the backend server'
    )
    parser.add_argument(
        '--frontend',
        action='store_true',
        help='Start only the frontend server'
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help='Show version and system info'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run preflight checks and exit'
    )
    parser.add_argument(
        '--setup-guide',
        action='store_true',
        help='Print Docker/PostgreSQL setup steps and exit'
    )
    parser.add_argument(
        '--use-dev-db',
        action='store_true',
        help='Force the backend to use the local SQLite development database'
    )
    
    args = parser.parse_args()
    
    # Initialize process manager
    pm = ProcessManager()

    # Show version/info
    if args.version:
        logger.info("\n" + "=" * 80)
        logger.info("[INFO] SYSTEM INFORMATION")
        logger.info("=" * 80)
        logger.info(f"Project Root: {PROJECT_ROOT}")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Backend Directory: {BACKEND_DIR}")
        logger.info(f"Frontend Directory: {FRONTEND_DIR}")
        logger.info(f"Backend Python: {pm.backend_python}")
        logger.info(f"Backend Port: {BACKEND_PORT}")
        logger.info(f"Frontend Port: {FRONTEND_PORT}")
        logger.info("=" * 80 + "\n")
        return

    if args.check:
        checks_ok = pm.run_preflight_checks()
        if checks_ok:
            logger.info("[OK] Preflight checks passed")
            return
        logger.error("[FAIL] Preflight checks failed")
        sys.exit(1)

    if args.setup_guide:
        pm.print_database_setup_guide()
        return

    if args.use_dev_db:
        pm.use_dev_database = True
        logger.info("[INFO] Forced SQLite development database mode enabled")

    # Run preflight checks before launching services
    pm.run_preflight_checks()
    
    # Determine what to start
    if args.backend:
        logger.info("Starting backend only...")
        if pm.start_backend():
            logger.info("\n" + "=" * 80)
            logger.info(f"[ACCESS] API: http://127.0.0.1:{pm.backend_port}")
            logger.info(f"[ACCESS] Docs: http://127.0.0.1:{pm.backend_port}/docs")
            logger.info("=" * 80 + "\n")
            pm.monitor_processes()
    elif args.frontend:
        logger.info("Starting frontend only...")
        if pm.start_frontend():
            logger.info("\n" + "=" * 80)
            logger.info("[BROWSER] OPEN THIS URL:")
            logger.info(f"          >>> http://localhost:{pm.frontend_port} <<<")
            logger.info("=" * 80 + "\n")
            pm.monitor_processes()
    else:
        # Start both
        pm.run_all()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n[STOP] Application interrupted by user")
    except Exception as e:
        logger.error(f"[FATAL] Fatal error: {e}", exc_info=True)
        sys.exit(1)
