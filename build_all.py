import os
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    print(f"Running: {command} in {cwd or os.getcwd()}")
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        exit(result.returncode)

def build():
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    release_dir = root_dir / "release"
    
    if not release_dir.exists():
        release_dir.mkdir()

    # 1. Build Backend
    print("--- Step 1: Building Backend ---")
    run_command("poetry run python build_backend.py", cwd=str(backend_dir))
    
    # 2. Build Frontend and Electron Package
    print("\n--- Step 2: Building Frontend and Electron Package ---")
    # Ensure dependencies are installed
    # run_command("npm install", cwd=str(frontend_dir)) 
    run_command("npm run build", cwd=str(frontend_dir))
    
    print("\n--- Build All Completed ---")
    print(f"Check the '{release_dir}' directory for the output.")

if __name__ == "__main__":
    build()
