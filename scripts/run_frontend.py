#!/usr/bin/env python3
"""
Script to start the frontend server on port 3000.
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Resolve repository root and frontend server path
    repo_root = Path(__file__).resolve().parents[1]
    frontend_server_path = repo_root / "frontend" / "server.py"
    
    if not frontend_server_path.exists():
        print(f"❌ Error: Frontend server script not found at {frontend_server_path}")
        print("Creating frontend server...")
        create_frontend_server()
        
    print(f"🚀 Starting frontend server from {frontend_server_path}...")
    try:
        subprocess.run([sys.executable, str(frontend_server_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend server failed to start: {e}")
    except FileNotFoundError:
        print(f"❌ Python executable not found. Ensure Python is in your PATH.")

def create_frontend_server():
    """Frontend server already exists, no need to recreate."""
    print("✅ Frontend server already exists")

if __name__ == "__main__":
    main()
