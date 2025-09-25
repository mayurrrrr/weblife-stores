"""Configuration settings for the Laptop Intelligence Engine."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Database - Use absolute path to ensure it works regardless of working directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "laptop_intelligence.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Debug: Show database path
print(f"🗄️  Database path: {DATABASE_PATH}")
print(f"🔗 Database URL: {DATABASE_URL}")
print(f"📁 Database exists: {DATABASE_PATH.exists()}")

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Debug: Check if API key is loaded
if GEMINI_API_KEY:
    print(f"✅ Gemini API key loaded successfully")
else:
    print("⚠️  Gemini API key not found - AI features will be limited")

# Note: Scraping URLs are now defined in backend/services/targets.py

# Note: PDF_MAPPINGS moved to backend/services/targets.py

# API settings
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Note: Scraping settings are now defined in backend/services/unified_scraper.py
