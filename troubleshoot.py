#!/usr/bin/env python3
"""
Crypto Arbitrage Troubleshooting Script
Diagnoses and fixes common issues in the system.
"""

import os
import sys
import subprocess
import time
import psutil
import redis
from pathlib import Path

# Colors for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def check_redis():
    """Check Redis connection and health."""
    print_header("REDIS DIAGNOSTICS")
    
    try:
        # Check if Redis is running
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print_success("Redis is running and responding")
        
        # Check Redis info
        info = redis_client.info()
        print_info(f"Redis version: {info.get('redis_version')}")
        print_info(f"Used memory: {info.get('used_memory_human')}")
        print_info(f"Connected clients: {info.get('connected_clients')}")
        
        # Test all databases
        for db in [0, 1, 2]:
            try:
                test_client = redis.Redis(host='localhost', port=6379, db=db)
                test_client.ping()
                print_success(f"Database {db}: OK")
            except Exception as e:
                print_error(f"Database {db}: {e}")
                
    except redis.ConnectionError:
        print_error("Redis is not running or not accessible")
        print_info("Try: brew services start redis (macOS) or sudo systemctl start redis (Linux)")
        return False
    except Exception as e:
        print_error(f"Redis error: {e}")
        return False
    
    return True

def check_database():
    """Check database status and locks."""
    print_header("DATABASE DIAGNOSTICS")
    
    db_path = Path("db.sqlite3")
    if not db_path.exists():
        print_error("Database file does not exist")
        print_info("Run: python manage.py migrate")
        return False
    
    print_success(f"Database file exists: {db_path}")
    print_info(f"Database size: {db_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Check for database locks
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print_success(f"Database accessible, {len(tables)} tables found")
        conn.close()
        
        # Check for WAL mode
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        if mode == 'wal':
            print_success("Database is in WAL mode (good for concurrent access)")
        else:
            print_warning(f"Database is in {mode} mode (may cause locks)")
        conn.close()
        
    except sqlite3.OperationalError as e:
        print_error(f"Database is locked or corrupted: {e}")
        return False
    except Exception as e:
        print_error(f"Database error: {e}")
        return False
    
    return True

def check_celery_processes():
    """Check for existing Celery processes."""
    print_header("CELERY PROCESS DIAGNOSTICS")
    
    celery_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'celery' in cmdline and 'python' in cmdline:
                celery_processes.append({
                    'pid': proc.info['pid'],
                    'cmd': cmdline
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if celery_processes:
        print_warning(f"Found {len(celery_processes)} existing Celery processes:")
        for proc in celery_processes:
            print(f"  PID {proc['pid']}: {proc['cmd'][:80]}...")
        
        response = input(f"\n{Colors.YELLOW}Kill these processes? [y/N]: {Colors.ENDC}")
        if response.lower() == 'y':
            for proc in celery_processes:
                try:
                    os.kill(proc['pid'], 9)
                    print_success(f"Killed process {proc['pid']}")
                except Exception as e:
                    print_error(f"Failed to kill process {proc['pid']}: {e}")
    else:
        print_success("No existing Celery processes found")
    
    return len(celery_processes) == 0

def check_log_files():
    """Check log file permissions and sizes."""
    print_header("LOG FILE DIAGNOSTICS")
    
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print_warning("Logs directory does not exist, creating...")
        logs_dir.mkdir(exist_ok=True)
        print_success("Created logs directory")
    
    log_files = [
        "celery-worker.log",
        "celery-beat.log",
        "crypto_arbitrage.log",
        "arbitrage.log"
    ]
    
    for log_file in log_files:
        log_path = logs_dir / log_file
        if log_path.exists():
            size_mb = log_path.stat().st_size / 1024 / 1024
            if size_mb > 100:
                print_warning(f"{log_file}: {size_mb:.2f} MB (large)")
            else:
                print_success(f"{log_file}: {size_mb:.2f} MB")
        else:
            print_info(f"{log_file}: Does not exist (will be created)")

def check_async_issues():
    """Check for common async/sync issues."""
    print_header("ASYNC/SYNC DIAGNOSTICS")
    
    # Check if asgiref is installed
    try:
        import asgiref
        print_success(f"asgiref installed: {asgiref.__version__}")
    except ImportError:
        print_error("asgiref not installed")
        print_info("Run: pip install asgiref")
        return False
    
    # Check Django version
    try:
        import django
        print_success(f"Django version: {django.__version__}")
        if django.VERSION < (4, 0):
            print_warning("Django version is old, consider upgrading")
    except ImportError:
        print_error("Django not installed")
        return False
    
    return True

def fix_permissions():
    """Fix common permission issues."""
    print_header("FIXING PERMISSIONS")
    
    # Fix log directory permissions
    logs_dir = Path("logs")
    if logs_dir.exists():
        try:
            os.chmod(str(logs_dir), 0o755)
            print_success("Fixed logs directory permissions")
        except Exception as e:
            print_error(f"Failed to fix logs permissions: {e}")
    
    # Fix database permissions
    db_path = Path("db.sqlite3")
    if db_path.exists():
        try:
            os.chmod(str(db_path), 0o644)
            print_success("Fixed database file permissions")
        except Exception as e:
            print_error(f"Failed to fix database permissions: {e}")

def run_test_task():
    """Run a test Celery task."""
    print_header("TESTING CELERY TASKS")
    
    try:
        # Set up Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()
        
        from config.celery import debug_task
        
        print_info("Running test task...")
        result = debug_task.delay()
        
        # Wait for result
        timeout = 10
        start_time = time.time()
        while not result.ready() and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        if result.ready():
            print_success("Test task completed successfully")
            return True
        else:
            print_error("Test task timed out")
            return False
            
    except Exception as e:
        print_error(f"Failed to run test task: {e}")
        return False

def main():
    """Run all diagnostics."""
    print(f"{Colors.BOLD}{Colors.PURPLE}")
    print("🔧 CRYPTO ARBITRAGE TROUBLESHOOTING TOOL")
    print("==========================================")
    print(f"{Colors.ENDC}")
    
    issues_found = []
    
    # Run diagnostics
    if not check_redis():
        issues_found.append("Redis connection issues")
    
    if not check_database():
        issues_found.append("Database issues")
    
    if not check_celery_processes():
        issues_found.append("Celery process conflicts")
    
    check_log_files()
    
    if not check_async_issues():
        issues_found.append("Async/sync compatibility issues")
    
    # Fix common issues
    fix_permissions()
    
    # Test Celery if no major issues
    if not issues_found:
        print_info("Running Celery test...")
        if not run_test_task():
            issues_found.append("Celery task execution")
    
    # Summary
    print_header("SUMMARY")
    
    if issues_found:
        print_error(f"Found {len(issues_found)} issues:")
        for issue in issues_found:
            print(f"  - {issue}")
        
        print(f"\n{Colors.YELLOW}Recommended actions:{Colors.ENDC}")
        print("1. Run: make clean")
        print("2. Run: make setup")
        print("3. Run: make start")
        
    else:
        print_success("No major issues found!")
        print_info("System appears to be ready")
    
    print(f"\n{Colors.CYAN}For more help:{Colors.ENDC}")
    print("- Check logs: make logs")
    print("- Debug worker: make debug-worker")
    print("- Debug beat: make debug-beat")

if __name__ == "__main__":
    main()