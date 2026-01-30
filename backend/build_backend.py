import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build():
    backend_dir = Path(__file__).parent
    dist_dir = backend_dir / "dist_py"
    build_dir = backend_dir / "build_py"
    
    # Clean up previous builds
    def on_rm_error(func, path, exc_info):
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if dist_dir.exists():
        try:
            shutil.rmtree(dist_dir)
        except Exception:
            print(f"Warning: Could not fully clean {dist_dir}, proceeding anyway...")
            
    if build_dir.exists():
        try:
            shutil.rmtree(build_dir)
        except Exception:
            print(f"Warning: Could not fully clean {build_dir}, proceeding anyway...")
        
    print("Building Backend with PyInstaller...")
    
    PyInstaller.__main__.run([
        'src/main.py',
        '--name=pdf-toolbox-server',
        '--onefile',
        '--clean',
        f'--distpath={dist_dir}',
        f'--workpath={build_dir}',
        # Add ocrmypdf data files
        '--collect-data=ocrmypdf',
        # Hidden imports for FastAPI and Uvicorn
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.websockets',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.lifespan.on',
        # Add src as a data path or ensure it's in path
        '--paths=src',
    ])
    
    print(f"Backend build completed. Executable at: {dist_dir}/pdf-toolbox-server.exe")

if __name__ == "__main__":
    build()
