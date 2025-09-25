#!/usr/bin/env python3
"""
Startup script for the Laptop Intelligence Engine.
This script handles the complete setup and launch process.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add backend directory to Python path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "backend"))

def check_requirements():
    """Check if all requirements are installed."""
    try:
        import fastapi
        import uvicorn
        import playwright
        import sqlalchemy
        import fitz  # PyMuPDF
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_playwright():
    """Check if Playwright browsers are installed."""
    try:
        result = subprocess.run(
            ["playwright", "install", "--help"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print("✅ Playwright is available")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Playwright browsers may not be installed")
    print("Please run: playwright install chromium")
    return False

def check_env_file():
    """Check if .env file exists."""
    if Path(".env").exists():
        print("✅ Environment file found")
        return True
    else:
        print("⚠️  No .env file found")
        print("Please copy env_example.txt to .env and configure your API keys")
        return False

def check_database():
    """Check if database exists, create if not."""
    db_file = Path("data/laptop_intelligence.db")
    if db_file.exists():
        print("✅ Database file found")
        return True
    else:
        print("⚠️  Database not found, will be created during data ingestion")
        return False

async def run_data_ingestion():
    """Run the data ingestion process."""
    print("\n🔄 Starting data ingestion...")
    try:
        from services.ingest_data import DataIngestion
        ingestion = DataIngestion()
        await ingestion.run_full_ingestion(clear_existing=True)
        print("✅ Data ingestion completed successfully")
        return True
    except Exception as e:
        print(f"❌ Data ingestion failed: {e}")
        return False

def start_server():
    """Start the FastAPI server."""
    print("\n🚀 Starting the Laptop Intelligence Engine server...")
    print("Server will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    # Change to backend directory and add to path
    backend_dir = Path(__file__).parent.parent / "backend"
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))
    
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")

async def main():
    """Main startup function."""
    print("🎯 Laptop Intelligence Engine - Startup Script")
    print("=" * 50)
    
    # Check requirements
    print("\n📋 Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    
    if not check_playwright():
        print("Warning: Playwright may not work properly")
    
    check_env_file()
    has_db = check_database()
    
    # Ask user if they want to run data ingestion
    if not has_db or input("\n🔄 Run data ingestion? (y/N): ").lower().startswith('y'):
        success = await run_data_ingestion()
        if not success:
            print("⚠️  Data ingestion failed, but continuing with server startup...")
    
    # Start the server
    start_server()

if __name__ == "__main__":
    asyncio.run(main())
