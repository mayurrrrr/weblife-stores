"""Configuration settings for the Laptop Intelligence Engine."""

import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = "sqlite:///data/laptop_intelligence.db"

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Debug: Check if API key is loaded
if GEMINI_API_KEY:
    print(f"✅ Gemini API key loaded successfully")
else:
    print("⚠️  Gemini API key not found - AI features will be limited")

# Target URLs for scraping
LENOVO_E14_INTEL_URL = "https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpade/thinkpad-e14-gen-5-14-inch-intel/len101t0064"
LENOVO_E14_AMD_URL = "https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpade/thinkpad-e14-gen-5-14-inch-amd/len101t0068"
HP_PROBOOK_440_URL = "https://www.hp.com/us-en/shop/pdp/hp-probook-440-14-inch-g11-notebook-pc"
HP_PROBOOK_450_URL = "https://www.hp.com/us-en/shop/pdp/hp-probook-450-156-inch-g10-notebook-pc-wolf-pro-security-edition-p-8l0e0ua-aba-1"

SCRAPING_URLS = {
    "lenovo_e14_intel": LENOVO_E14_INTEL_URL,
    "lenovo_e14_amd": LENOVO_E14_AMD_URL,
    "hp_probook_440": HP_PROBOOK_440_URL,
    "hp_probook_450": HP_PROBOOK_450_URL,
}

# PDF file mappings
PDF_MAPPINGS = {
    "lenovo_e14_intel": "../../data/pdfs/ThinkPad_E14_Gen_5_Intel_Spec.pdf",
    "lenovo_e14_amd": "../../data/pdfs/ThinkPad_E14_Gen_5_AMD_Spec.pdf",
    "hp_probook_440": "../../data/pdfs/hp-probook-440.pdf",
    "hp_probook_450": "../../data/pdfs/hp-probook-450.pdf",
}

# API settings
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Scraping settings
SCRAPING_DELAY = 2  # seconds between requests
HEADLESS_BROWSER = True
BROWSER_TIMEOUT = 30000  # milliseconds
